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
import sys
from audit_kernel_instructions import image_layout
from verify_experimental_artifact import verify
from boot_contract import Region, PAGE, encode_boot_args, validate_placement, uint

ROOT = Path(__file__).resolve().parents[2]


def run_case(directory, ram_base, outside_bootstrap_block=False, transfer_elf=None, handoff_bundle=None,ram_size=0x40000000,continuation=None,cpu_model=None,*,virtual_ram_base=0xfffffff000000000):
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
    from unicorn import arm64_const as regs
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
    checked = verify(directory)
    raw = (directory/'note10-experimental.macho').read_bytes()
    virtual_ram = uint(virtual_ram_base)  # Original default; optional explicit synthetic contract.
    image_base = min(s['virtual_address'] for s in checked['segments'] if s['virtual_size'])
    physical_image = ram_base + image_base-virtual_ram
    span = max(s['virtual_address']+s['virtual_size'] for s in checked['segments'])-image_base
    rounded = (span+0x3fff)&~0x3fff
    bundle=None;buffers=None
    if handoff_bundle is not None:
        from handoff_bundle import load
        bundle,buffers=load(handoff_bundle,kernel_sha256=checked['sha256'])
        if bundle['plan']['ram']!={'start':ram_base,'size':ram_size} or bundle['plan']['virtual_base']!=virtual_ram:
            raise ValueError('Bundle does not match this explicit RAM model')
        kernel_buffer=next(b for b in bundle['buffers'] if b['file']=='kernel.mem')
        if kernel_buffer['physical_address']!=physical_image or kernel_buffer['size']!=rounded:
            raise ValueError('Bundle kernel placement differs from executable')
        if bundle['xnu_entry_physical']!=ram_base+int(checked['entry_virtual_address'],16)-virtual_ram:
            raise ValueError('Bundle entry differs from executable')
        if transfer_elf is None or bundle['adapter_elf_sha256']!=hashlib.sha256(transfer_elf.read_bytes()).hexdigest():
            raise ValueError('Bundle adapter source differs')
    uc = Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    if cpu_model is not None:
        if cpu_model!='max':raise ValueError('Unsupported explicit synthetic CPU model')
        uc.ctl_set_cpu_model(regs.UC_CPU_ARM64_MAX)
    uc.mem_map(physical_image,rounded)
    if bundle is not None:
        # Make copying the full buffer (including zero BSS) observable.
        uc.mem_write(physical_image,b'\xa5'*rounded)
        uc.mem_write(physical_image,buffers['kernel.mem'])
        for segment in checked['segments']:
            pa=ram_base+segment['virtual_address']-virtual_ram
            count=segment['file_size'];offset=segment['file_offset']
            if count and bytes(uc.mem_read(pa,count))!=raw[offset:offset+count]:
                raise ValueError('Materialized kernel differs from source segment')
            zero=segment['virtual_size']-count
            if zero and any(uc.mem_read(pa+count,zero)):
                raise ValueError('Materialized kernel BSS was not zeroed')
    else:
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
    if bundle is not None:
        if outside_bootstrap_block:raise ValueError('A materialized bundle cannot be silently relocated')
        arguments=bundle['boot_args_physical']
        if bundle['plan']['device_tree_address']!=arguments+PAGE or bundle['plan']['adapter_address']!=arguments+2*PAGE:
            raise ValueError('This model requires contiguous metadata pages')
    uc.mem_map(arguments,0x10000)
    if not outside_bootstrap_block:
        validate_placement(ram=Region(ram_base,ram_size),reserved=[],occupied=[],
                           kernel=Region(physical_image,rounded),
                           arguments=Region(arguments,PAGE),top_of_kernel=physical_image+rounded)
    boot_args = encode_boot_args(virtual_base=virtual_ram,physical_base=ram_base,
                                 memory_size=ram_size,top_of_kernel=physical_image+rounded)
    if bundle is not None:boot_args=buffers['boot-args.mem'][:1152]
    uc.mem_write(arguments,bytes(boot_args));uc.reg_write(regs.UC_ARM64_REG_X0,arguments)
    pc = ram_base+int(checked['entry_virtual_address'],16)-virtual_ram
    adapter_record = None
    if transfer_elf is not None:
        sys.path.insert(0,str(ROOT/'note10/shim'))
        from test_cap_entry import elf
        adapter_segments,adapter_symbols = elf(transfer_elf.read_bytes())
        adapter_base = arguments+0x8000
        for va,memsize,payload in adapter_segments:
            if va+memsize > 0x4000:raise ValueError('Adapter exceeds synthetic allocation')
            uc.mem_write(adapter_base+va,payload)
        adapter_record=adapter_base+adapter_symbols['n10_transfer_record']
        uc.mem_write(adapter_record+16,struct.pack('<QQ',arguments,pc))
        pc_start=adapter_base+adapter_symbols['_start']
        # The real recovery's kexec tail clears x0-x3; require the adapter to
        # supply x0 rather than inheriting the test's direct-entry argument.
        for index in range(4):uc.reg_write(getattr(regs,'UC_ARM64_REG_X'+str(index)),0)
        if bundle is not None:
            from handoff_bundle import materialize_adapter
            canonical,relative_start,relative_record=materialize_adapter(transfer_elf.read_bytes())
            canonical=bytearray(canonical)
            struct.pack_into('<QQ',canonical,relative_record+16,arguments,pc)
            if bytes(canonical)!=buffers['adapter.mem'] or bundle['adapter_entry_physical']!=adapter_base+relative_start or bundle['adapter_record_physical']!=adapter_base+relative_record:
                raise ValueError('Materialized adapter differs from source ELF')
            for name in ('boot-args.mem','device-tree.mem','adapter.mem'):
                item=next(b for b in bundle['buffers'] if b['file']==name)
                uc.mem_write(item['physical_address'],buffers[name])
            adapter_record=bundle['adapter_record_physical'];pc_start=bundle['adapter_entry_physical']
    else:pc_start=pc
    md = Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    state = {'currentel':4,'clidr_el1':0,'ctr_el0':0x8444c004,'sctlr_el1':0,
             'midr_el1':0x410fd050,'id_aa64mmfr0_el1':0x100000,'csselr_el1':0,
             'cntkctl_el1':0,'cntfrq_el0':26000000,'daif':0}
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
            if reg in ('daifset','daifclr'):
                if not 0<=number<=15:raise ValueError('Invalid DAIF immediate')
                mask=number<<6
                state['daif']=(state['daif']|mask) if reg=='daifset' else (state['daif']&~mask)
            state[reg]=number;writes.append({'register':reg,'value':hex(number)})
            operations['synthetic_msr']+=1
        elif ins.mnemonic in ('dc','ic','tlbi','dsb','dmb','isb'):
            operations['synthetic_'+ins.mnemonic]+=1
        else:return
        engine.reg_write(regs.UC_ARM64_REG_PC,address+4)
    stores = []; stored_bytes = 0
    adapter_stores = []
    def write(engine,access,address,size,number,_):
        nonlocal stored_bytes
        if adapter_record is not None and adapter_record+48 <= address and address+size <= adapter_record+64:
            adapter_stores.append(address);return
        if not physical_image <= address or address+size > physical_image+rounded:
            raise ValueError('Startup store left modeled kernel RAM: '+hex(address))
        stores.append(address);stored_bytes += size
    code_hook=uc.hook_add(UC_HOOK_CODE,instruction)
    write_hook=uc.hook_add(UC_HOOK_MEM_WRITE,write)
    try:uc.emu_start(pc_start,physical_image+rounded,count=100000)
    except Exception as error:raise ValueError(str(error)+'\n'+'\n'.join(recent)) from error
    if not stop:raise ValueError('Entry failed to reach modeled MMU boundary\n'+'\n'.join(recent))
    if adapter_record is not None and struct.unpack('<Q',uc.mem_read(adapter_record+48,8))[0]!=1:
        raise ValueError('Adapter did not report its attempted entry branch')
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
    if bundle is not None:
        dt=bundle['plan']['device_tree_address'];length=bundle['device_tree_length']
        virtual_dt=virtual_ram+dt-ram_base
        for delta in (0,length-1):
            if walk(dt+delta,False)!=dt+delta or walk(virtual_dt+delta,True)!=dt+delta:
                raise ValueError('Materialized ADT outside bootstrap mappings')
        if bytes(uc.mem_read(dt,PAGE))!=buffers['device-tree.mem']:
            raise ValueError('Entry changed materialized ADT')
    endpoints = []
    for segment in checked['segments']:
        if not segment['virtual_size']: continue
        for va in (segment['virtual_address'],segment['virtual_address']+segment['virtual_size']-1):
            pa = ram_base+va-virtual_ram
            if walk(va,True) != pa or walk(pa,False) != pa:
                raise ValueError('Kernel segment endpoint outside actual bootstrap mapping')
            endpoints.append(hex(va))
    result={'synthetic_cpu_model':cpu_model or 'unicorn-default','synthetic_ram_base':hex(ram_base),'synthetic_ram_size':hex(ram_size),'synthetic_kernel_physical':hex(physical_image),
            'synthetic_boot_args_physical':hex(arguments),'instructions':count,'stop':stop,
            'system_operations':dict(operations),'register_writes':writes,'modeled_daif_before_mmu':state['daif'],
            'store_count':len(stores),'stored_bytes':stored_bytes,
            'adapter_status_store_count':len(adapter_stores),
            'bootstrap_table_pages_primed_and_cleared':4,
            'segment_virtual_and_identity_endpoints_checked':endpoints,
            'store_range':[hex(min(stores)),hex(max(stores))],
            'translations':{k:hex(v) for k,v in translations.items()},'tcr_el1':hex(tcr),'passed':True}
    if continuation is not None:
        result['continuation']=continuation(uc=uc,md=md,state=state,stop=stop,symbols=symbols,
            physical_image=physical_image,rounded=rounded,arguments=arguments,boot_args=boot_args,
            virtual_ram=virtual_ram,ram_base=ram_base,walk=walk,
            code_hook=code_hook,write_hook=write_hook,banked_sp=banked_sp,sp_select=sp_select,
            kernel_raw=raw,kernel_segments=checked['segments'])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    parser.add_argument('--adapter',type=Path,help='PC-only post-shutdown entry adapter ELF')
    parser.add_argument('--observed-profile',type=Path,help='Compare modeled TCR with hash-bound Linux CPU observations')
    args = parser.parse_args()
    cases = [run_case(args.directory,base,transfer_elf=args.adapter) for base in (0x80000000,0x100000000)]
    negative = False
    try:run_case(args.directory,0x80000000,outside_bootstrap_block=True,transfer_elf=args.adapter)
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
    if args.adapter is not None:result['adapter_sha256']=hashlib.sha256(args.adapter.read_bytes()).hexdigest()
    if args.observed_profile is not None:
        from observed_profile import load,check_tcr
        profile=load(args.observed_profile)
        result['observed_profile_sha256']=hashlib.sha256(args.observed_profile.read_bytes()).hexdigest()
        result['observed_capacity_checks']=[check_tcr(profile,int(case['tcr_el1'],16)) for case in cases]
    output='adapter-linked-entry-test-result.json' if args.adapter is not None else 'linked-entry-test-result.json'
    if args.observed_profile is not None:output='observed-'+output
    (ROOT/'note10/private'/output).write_text(json.dumps(result,indent=2))
    print(json.dumps({'passed':True,'cases':len(cases),'instructions':[c['instructions'] for c in cases],
                      'stop':'before_mmu_enable','hardware_verified':False}))
