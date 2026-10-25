"""Execute the actual static PID1 ELF with modeled Linux syscalls on a PC."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from run_probe import ROOT


def test(elf_path):
    from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
    from unicorn import arm64_const as r
    from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
    sys.path.insert(0,str(ROOT/'note10/shim'))
    from test_cap_entry import elf
    raw=elf_path.read_bytes();segments,symbols=elf(raw)
    engine=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    mapped=[]
    for address,size,data in segments:
        start=address&~0xffff;end=(address+size+0xffff)&~0xffff
        if any(start<b and a<end for a,b in mapped):raise ValueError('Overlapping init mappings')
        engine.mem_map(start,end-start);engine.mem_write(address,data);mapped.append((start,end))
    calls=[];message=None
    md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    def instruction(uc,address,size,_):
        nonlocal message
        ins=next(md.disasm(bytes(uc.mem_read(address,4)),address))
        if ins.mnemonic!='svc':return
        number=uc.reg_read(r.UC_ARM64_REG_X8);calls.append(number)
        if number==64:
            if calls!=[64] or uc.reg_read(r.UC_ARM64_REG_X0)!=1:raise ValueError('Unexpected write call')
            pointer=uc.reg_read(r.UC_ARM64_REG_X1);length=uc.reg_read(r.UC_ARM64_REG_X2)
            if not 0<length<=128:raise ValueError('Unexpected init message length')
            message=bytes(uc.mem_read(pointer,length)).decode('ascii')
            if not message.startswith('N10INIT1 IDLE '):raise ValueError('Unexpected init message')
            uc.reg_write(r.UC_ARM64_REG_X0,length)
        elif number==73:
            args=[uc.reg_read(getattr(r,'UC_ARM64_REG_X'+str(i))) for i in range(5)]
            if calls[0]!=64 or args!=[0,0,0,0,8]:raise ValueError('ppoll is not an indefinite idle wait')
            if calls.count(73)==3:uc.emu_stop();return
            # Model signal interruption; code must return to the idle wait.
            uc.reg_write(r.UC_ARM64_REG_X0,(-4)&((1<<64)-1))
        else:raise ValueError('Unexpected syscall: '+str(number))
        uc.reg_write(r.UC_ARM64_REG_PC,address+4)
    engine.hook_add(UC_HOOK_CODE,instruction)
    # Deliberately unmapped SP: this freestanding program must not use a stack.
    engine.reg_write(r.UC_ARM64_REG_SP,0)
    engine.emu_start(symbols['_start'],max(end for _,end in mapped),count=100)
    if calls!=[64,73,73,73]:raise ValueError('Init did not remain in its idle loop')
    return {'passed':True,'elf_sha256':hashlib.sha256(raw).hexdigest(),'syscall_sequence':calls,
            'message':message,'scope':'Real PID1 instructions; modeled write/ppoll, not a phone execution',
            'device_operations':[],'xnu_executed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('elf',type=Path);parser.add_argument('--report',type=Path)
    args=parser.parse_args();result=test(args.elf)
    if args.report:
        if not args.report.resolve().is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Private report required')
        args.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
