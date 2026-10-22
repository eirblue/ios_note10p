"""Execute the linked XNU entry up to the MMU-enable write in a synthetic model.

Uses real kernel instructions and stores. System registers, cache/TLB effects
and all physical RAM addresses are synthetic, not a device boot result.
"""
import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import struct
from audit_kernel_instructions import image_layout
from verify_experimental_artifact import verify
from boot_contract import Region, PAGE, encode_boot_args, validate_placement

ROOT = Path(__file__).resolve().parents[2]


def run_case(directory, ram_base, outside_bootstrap_block=False):
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
    from unicorn import arm64_const as regs
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
    checked = verify(directory)
    raw = (directory/'note10-experimental.macho').read_bytes()
    virtual_ram = 0xfffffff000000000  # Synthetic virtual/physical mapping contract.
    image_base = min(s['virtual_address'] for s in checked['segments'] if s['virtual_size'])
    physical_image = ram_base + image_base-virtual_ram
    span = max(s['virtual_address']+s['virtual_size'] for s in checked['segments'])-image_base
    rounded = (span+0x3fff)&~0x3fff
    uc = Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    uc.mem_map(physical_image,rounded)
    for segment in checked['segments']:
        if not segment['file_size']:continue
        pa = ram_base+segment['virtual_address']-virtual_ram
        uc.mem_write(pa,raw[segment['file_offset']:segment['file_offset']+segment['file_size']])
    symbols = {name:address for address,name in image_layout(raw)[2]}
    tables = ram_base+symbols['_bootstrap_pagetables']-virtual_ram
    # Prime the four pages that start.s must clear; zero-filled emulated RAM
    # would otherwise hide a broken initialization loop.
    uc.mem_write(tables,b'\xa5'*0x10000)
    # Startup excludes memory before the block containing the image header.
    # Keep metadata in that first block under the conservative producer policy.
    arguments = ram_base+0x2000000 if outside_bootstrap_block else (physical_image & ~0x1ffffff)+0x4000
    uc.mem_map(arguments,0x10000)
    if not outside_bootstrap_block:
        validate_placement(ram=Region(ram_base,0x40000000),reserved=[],occupied=[],
                           kernel=Region(physical_image,rounded),
                           arguments=Region(arguments,PAGE),top_of_kernel=physical_image+rounded)
    boot_args = encode_boot_args(virtual_base=virtual_ram,physical_base=ram_base,
                                 memory_size=0x40000000,top_of_kernel=physical_image+rounded)
    uc.mem_write(arguments,bytes(boot_args));uc.reg_write(regs.UC_ARM64_REG_X0,arguments)
    pc = ram_base+int(checked['entry_virtual_address'],16)-virtual_ram
    md = Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    state = {'currentel':4,'clidr_el1':0,'ctr_el0':0x8444c004,'sctlr_el1':0,
             'midr_el1':0x410fd050,'id_aa64mmfr0_el1':0x100000,'csselr_el1':0}
    writes = []; operations = Counter(); recent = deque(maxlen=16)
    count = 0; stop = None; sp_select = 0; banked_sp = {0:0,1:0}
    def gpr(name):
        if name == 'xzr':return None
        return getattr(regs,'UC_ARM64_REG_'+name.upper())
    def value(name):
        if name.startswith('#'):return int(name[1:],0)
        register = gpr(name);return uc.reg_read(register) if register is not None else 0
    def instruction(engine,address,size,_):
        nonlocal count,stop,sp_select
        count += 1
        ins = next(md.disasm(bytes(engine.mem_read(address,4)),address))
        recent.append(hex(address)+' '+ins.mnemonic+' '+ins.op_str)
        operands = [x.strip().lower() for x in ins.op_str.split(',')]
        if ins.mnemonic == 'mrs':
            dst,reg = operands
            if reg not in state:raise ValueError('Unmodeled system register read: '+reg)
            engine.reg_write(gpr(dst),state[reg]);operations['synthetic_mrs']+=1
        elif ins.mnemonic == 'msr':
            reg,src = operands;number = value(src)
            if reg == 'sctlr_el1' and number & 1:
                stop = {'reason':'before_mmu_enable','address':hex(address),'sctlr_value':hex(number)}
                engine.emu_stop();return
            if reg == 'spsel':
                banked_sp[sp_select]=engine.reg_read(regs.UC_ARM64_REG_SP)
                sp_select=number;engine.reg_write(regs.UC_ARM64_REG_SP,banked_sp[number])
            state[reg]=number;writes.append({'register':reg,'value':hex(number)})
            operations['synthetic_msr']+=1
        elif ins.mnemonic in ('dc','ic','tlbi','dsb','dmb','isb'):
            operations['synthetic_'+ins.mnemonic]+=1
        else:return
        engine.reg_write(regs.UC_ARM64_REG_PC,address+4)
    stores = []; stored_bytes = 0
    def write(engine,access,address,size,number,_):
        nonlocal stored_bytes
        if not physical_image <= address or address+size > physical_image+rounded:
            raise ValueError('Startup store left modeled kernel RAM: '+hex(address))
        stores.append(address);stored_bytes += size
    uc.hook_add(UC_HOOK_CODE,instruction);uc.hook_add(UC_HOOK_MEM_WRITE,write)
    try:uc.emu_start(pc,physical_image+rounded,count=100000)
    except Exception as error:raise ValueError(str(error)+'\n'+'\n'.join(recent)) from error
    if not stop:raise ValueError('Entry failed to reach modeled MMU boundary\n'+'\n'.join(recent))
    table_bytes = bytes(uc.mem_read(tables,0x10000))
    if b'\xa5'*8 in table_bytes:raise ValueError('Bootstrap table initialization left stale descriptors')
    if bytes(uc.mem_read(arguments,len(boot_args))) != boot_args:raise ValueError('Entry changed boot arguments')
    for reg in ('tcr_el1','ttbr0_el1','ttbr1_el1','mair_el1','vbar_el1'):
        if reg not in state:raise ValueError('Required startup register was not configured: '+reg)
    tcr = state['tcr_el1']
    def walk(va,high):
        if ((tcr>>30)&3 if high else (tcr>>14)&3) != (1 if high else 2):
            raise ValueError('This model expects the compiled 16K bootstrap granule')
        bits = 64-((tcr>>16)&63 if high else tcr&63)
        levels = (bits-14+10)//11;first_level=4-levels
        if first_level != 1:raise ValueError('Unexpected bootstrap root level')
        table = state['ttbr1_el1' if high else 'ttbr0_el1'] & 0x0000ffffffffc000
        for level in range(first_level,4):
            shift = 14+(3-level)*11
            width = bits-shift if level==first_level else 11
            slot = (va>>shift)&((1<<width)-1)
            desc = struct.unpack('<Q',uc.mem_read(table+slot*8,8))[0]
            if desc&3==1 and level in (1,2) or desc&3==3 and level==3:
                return (desc & 0x0000ffffffffffff & ~((1<<shift)-1))+(va&((1<<shift)-1))
            if desc&3 != 3:raise ValueError('Invalid bootstrap translation descriptor')
            table = desc & 0x0000ffffffffc000
        raise ValueError('No bootstrap translation')
    entry_va = int(checked['entry_virtual_address'],16)
    try:
        args_identity=walk(arguments,False)
        args_virtual=walk(virtual_ram+arguments-ram_base,True)
    except ValueError as error:
        raise ValueError('Boot arguments outside actual bootstrap mapping') from error
    translations={'identity_entry':walk(pc,False),'kernel_entry':walk(entry_va,True),
                  'boot_args_identity':args_identity,'boot_args_virtual':args_virtual}
    if translations != {'identity_entry':pc,'kernel_entry':pc,'boot_args_identity':arguments,'boot_args_virtual':arguments}:
        raise ValueError('Bootstrap tables do not map synthetic entry/arguments as expected')
    endpoints = []
    for segment in checked['segments']:
        if not segment['virtual_size']: continue
        for va in (segment['virtual_address'],segment['virtual_address']+segment['virtual_size']-1):
            pa = ram_base+va-virtual_ram
            if walk(va,True) != pa or walk(pa,False) != pa:
                raise ValueError('Kernel segment endpoint outside actual bootstrap mapping')
            endpoints.append(hex(va))
    return {'synthetic_ram_base':hex(ram_base),'synthetic_kernel_physical':hex(physical_image),
            'synthetic_boot_args_physical':hex(arguments),'instructions':count,'stop':stop,
            'system_operations':dict(operations),'register_writes':writes,
            'store_count':len(stores),'stored_bytes':stored_bytes,
            'bootstrap_table_pages_primed_and_cleared':4,
            'segment_virtual_and_identity_endpoints_checked':endpoints,
            'store_range':[hex(min(stores)),hex(max(stores))],
            'translations':{k:hex(v) for k,v in translations.items()},'passed':True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    args = parser.parse_args()
    cases = [run_case(args.directory,base) for base in (0x80000000,0x100000000)]
    negative = False
    try:run_case(args.directory,0x80000000,outside_bootstrap_block=True)
    except ValueError as error:
        if str(error) != 'Boot arguments outside actual bootstrap mapping':raise
        negative = True
    if not negative:raise ValueError('Unmapped boot arguments were not rejected')
    import unicorn
    import capstone
    result={'cases':cases,'passed':True,'kernel_sha256':hashlib.sha256((args.directory/'note10-experimental.macho').read_bytes()).hexdigest(),
            'unicorn_version':unicorn.__version__,'capstone_version':capstone.__version__,
            'scope':'Real linked entry and table stores; synthetic EL1/register/cache/TLB model; stops before MMU enable',
            'cpu_cache_view':'Synthetic CLIDR=0; real cache maintenance not exercised',
            'unmapped_boot_args_negative_case_rejected':negative,
            'hardware_verified':False,'device_operations':[],'deployment_ready':False}
    (ROOT/'note10/private/linked-entry-test-result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'passed':True,'cases':len(cases),'instructions':[c['instructions'] for c in cases],
                      'stop':'before_mmu_enable','hardware_verified':False}))
