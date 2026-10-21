"""Execute the assembled entry under Unicorn with explicitly synthetic MRS/MSR views."""
import json
import hashlib
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'host-tools/python-packages'))
import unicorn
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm64_const as regs
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from decode_cap_record import decode

def elf(raw):
    assert raw[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',raw,18)[0]==183
    phoff,shoff=struct.unpack_from('<QQ',raw,32)
    phsize,phnum,shsize,shnum=struct.unpack_from('<4H',raw,54)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*shsize) for i in range(shnum)]
    symbols={}
    for section in sections:
        if section[1]!=2:continue
        stringtab=sections[section[6]]
        strings=raw[stringtab[4]:stringtab[4]+stringtab[5]]
        for p in range(section[4],section[4]+section[5],section[9]):
            name,_,_,_,value,_=struct.unpack_from('<IBBHQQ',raw,p)
            symbols[strings[name:].split(b'\0',1)[0].decode()]=value
    segments=[]
    for i in range(phnum):
        kind,flags,off,va,_,size,memsize,_=struct.unpack_from('<II6Q',raw,phoff+i*phsize)
        if kind==1:segments.append((va,memsize,raw[off:off+size]))
    assert all(s[1] not in (4,9) for s in sections), 'Unexpected relocations in linked entry'
    return segments,symbols

def run_case(segments,symbols,base,el,clidr,mmfr):
    uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    uc.mem_map(base,0x10000)
    for va,_,data in segments:uc.mem_write(base+va,data)
    record=base+symbols['n10_cap_record'];halt=base+symbols['n10_cap_halt']
    # A repeated entry must clear old data, including unprobed levels/reserved bytes.
    uc.mem_write(record+16,b'\xa5'*304)
    initial=[0x1111,0x2222,0x3333,0x4444]
    for i,v in enumerate(initial):uc.reg_write(getattr(regs,'UC_ARM64_REG_X'+str(i)),v)
    uc.reg_write(regs.UC_ARM64_REG_SP,0x30000000) # deliberately unmapped: no stack access allowed.
    values={'currentel':el,'daif':0x140,'mpidr_el1':0x80000100,'cntfrq_el0':26000000,
            'id_aa64mmfr0_el1':mmfr,'id_aa64mmfr1_el1':0x1122,'id_aa64isar0_el1':0x3344,
            'id_aa64isar1_el1':0x5566,'id_aa64pfr0_el1':0x7788,'ctr_el0':0x8444c004,
            'clidr_el1':clidr,'sctlr_el1':0x10,'tcr_el1':0x20,'ttbr0_el1':0x30,
            'ttbr1_el1':0x40,'vbar_el1':0x50,'sctlr_el2':0x60,'tcr_el2':0x70,'hcr_el2':0x80}
    selector=11;selected=[];reads=[];stopped=False
    md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    def gpr(name):return getattr(regs,'UC_ARM64_REG_'+name.upper())
    def instruction(engine,address,size,_):
        nonlocal selector,stopped
        if address==halt:stopped=True;engine.emu_stop();return
        ins=next(md.disasm(bytes(engine.mem_read(address,size)),address))
        operands=[p.strip().lower() for p in ins.op_str.split(',')]
        if ins.mnemonic=='mrs':
            dst,reg=operands;reads.append(reg)
            if reg=='csselr_el1':value=selector
            elif reg=='ccsidr_el1':
                assert not selector&1
                level=selector>>1
                assert level<7 and (clidr>>(level*3))&7 in (2,3,4)
                selected.append(level);value=0x12345000 | ((level+2)&7)
            else:
                assert reg in values,reg
                assert el in (4,8) or reg in ('currentel','daif')
                assert el==8 or not reg.endswith('_el2')
                value=values[reg]
            engine.reg_write(gpr(dst),value);engine.reg_write(regs.UC_ARM64_REG_PC,address+4)
        elif ins.mnemonic=='msr':
            reg,src=operands
            assert reg in ('csselr_el1','daifset'),reg
            if reg=='csselr_el1':selector=engine.reg_read(gpr(src))
            else:assert src=='#0xf'
            engine.reg_write(regs.UC_ARM64_REG_PC,address+4)
    def write(engine,access,address,size,value,_):assert record+16<=address and address+size<=record+320
    uc.hook_add(UC_HOOK_CODE,instruction);uc.hook_add(UC_HOOK_MEM_WRITE,write)
    uc.emu_start(base+symbols['_start'],base+0x10000,count=4000)
    assert stopped
    result=bytes(uc.mem_read(record,320))
    assert list(struct.unpack_from('<4Q',result,32))==initial
    assert struct.unpack_from('<Q',result,64)[0]==0x30000000
    if el not in (4,8):
        assert struct.unpack_from('<Q',result,16)[0]==2 and not selected
        return result
    parsed=decode(result)
    expected=[i for i in range(7) if (clidr>>(3*i))&7 in (2,3,4)]
    assert selected==expected and selector==11
    assert [c['level'] for c in parsed['caches']]==[i+1 for i in expected]
    assert [c['maintenance_line_bytes'] for c in parsed['caches']]==[1<<(((i+2)&7)+4) for i in expected]
    assert parsed['entry_el']==el>>2 and parsed['granules_stage1']['16k']=={0:False,1:True,2:True,15:'reserved_unknown'}[(mmfr>>20)&15]
    assert all(not reg.endswith('_el2') for reg in reads) if el==4 else 'hcr_el2' in reads
    return result

def main():
    binary=ROOT/'note10/private/cap-probe/cap-probe.elf'
    segments,symbols=elf(binary.read_bytes())
    cases=0;sample=None
    layouts=(0,3|(4<<3),1|(3<<3)|(4<<6),sum(4<<(3*i) for i in range(7)))
    for base in (0x100000,0x4000000,0x100000000):
        for el in (4,8):
            for clidr in layouts:
                for granule in (0,1,2,15):
                    sample=run_case(segments,symbols,base,el,clidr,granule<<20);cases+=1
        for el in (0,12):run_case(segments,symbols,base,el,0,0);cases+=1
    invalid=[sample[:-1],sample+b'\0',b'BADMAGIC'+sample[8:]]
    for offset,value in ((8,2),(12,319),(16,0),(16,2),(24,12),(280,1)):
        b=bytearray(sample);struct.pack_into('<I',b,offset,value);invalid.append(bytes(b))
    for b in invalid:
        try:decode(b)
        except ValueError:continue
        raise AssertionError('Malformed record accepted')
    report={'emulated_cases':cases,'decoder_negative_cases':len(invalid),'unicorn_version':unicorn.__version__,
            'elf_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
            'source_sha256':{name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                             for name in ('cap_entry.S','cap_record.h','cap_link.ld')},
            'system_register_reads_writes':'Synthetic hook values, not real CPU registers',
            'device_execution':False,'passed':True}
    (binary.parent/'test-result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
if __name__=='__main__':main()
