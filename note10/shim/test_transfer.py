"""Execute actual adapter instructions with synthetic privileged registers.

Stops at the target branch, before running a kernel. No hardware is accessed.
"""
import hashlib
import argparse
import json
from pathlib import Path
import struct
from test_cap_entry import elf
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm64_const as regs
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

ROOT = Path(__file__).resolve().parents[2]


def case(raw, base, *, el=4, sctlr=0, cntkctl=0, cntfrq=26000000, patch=None):
    segments,symbols = elf(raw)
    engine=Uc(UC_ARCH_ARM64,UC_MODE_ARM);engine.mem_map(base,0x10000)
    for va,_,data in segments:engine.mem_write(base+va,data)
    record=base+symbols['n10_transfer_record'];halt=base+symbols['n10_transfer_halt']
    target=0x50000000;arguments=0x60000000
    engine.mem_map(target,0x10000);engine.mem_map(arguments,0x10000)
    descriptor=bytearray(struct.pack('<8sII6Q',b'N10XFER1',1,64,arguments,target,0,0,99,99))
    if patch: patch(descriptor)
    engine.mem_write(record,bytes(descriptor))
    engine.reg_write(regs.UC_ARM64_REG_SP,0x70000000) # Unmapped: adapter must not use stack.
    for index in range(4):engine.reg_write(getattr(regs,'UC_ARM64_REG_X'+str(index)),0xdeadbeef)
    stopped=None;operations=[];count=0
    md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    def hook(uc,address,size,_):
        nonlocal stopped,count
        if address in (halt,target):
            stopped='target' if address==target else 'halt';uc.emu_stop();return
        count+=1
        ins=next(md.disasm(bytes(uc.mem_read(address,4)),address))
        operands=[x.strip().lower() for x in ins.op_str.split(',')]
        if ins.mnemonic=='mrs':
            dst,reg=operands
            if reg=='currentel':value=el
            elif reg=='sctlr_el1' and el==4:value=sctlr
            elif reg=='cntkctl_el1' and el==4:value=cntkctl
            elif reg=='cntfrq_el0' and el==4:value=cntfrq
            else:raise ValueError('Unexpected privileged read: '+reg)
            uc.reg_write(getattr(regs,'UC_ARM64_REG_'+dst.upper()),value)
        elif ins.mnemonic=='msr':
            if operands!=['daifset','#0xf'] or el!=4:raise ValueError('Unexpected state write')
            operations.append('synthetic interrupt mask')
        elif ins.mnemonic=='dsb':operations.append('synthetic barrier')
        else:return
        uc.reg_write(regs.UC_ARM64_REG_PC,address+4)
    def write(uc,access,address,size,value,_):
        if not record+48<=address or address+size>record+64:
            raise ValueError('Adapter write escaped status fields')
    engine.hook_add(UC_HOOK_CODE,hook);engine.hook_add(UC_HOOK_MEM_WRITE,write)
    engine.emu_start(base+symbols['_start'],base+0x10000,count=1000)
    if not stopped:raise ValueError('Adapter did not stop/transfer')
    result=bytes(engine.mem_read(record,64))
    if result[:48]!=descriptor[:48]:raise ValueError('Adapter modified input contract')
    status,observed=struct.unpack_from('<QQ',result,48)
    if stopped=='target':
        if [engine.reg_read(getattr(regs,'UC_ARM64_REG_X'+str(i))) for i in range(4)] != [arguments,0,0,0]:
            raise ValueError('Wrong XNU arguments')
    return dict(stopped=stopped,status=status,observed_sctlr=observed,instructions=count)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf',type=Path,default=ROOT/'note10/private/xnu-transfer/transfer.elf')
    binary=parser.parse_args().elf;raw=binary.read_bytes()
    results=[]
    malformed=[lambda b:b.__setitem__(slice(0,8),b'BADMAGIC'),
               lambda b:struct.pack_into('<I',b,8,2),lambda b:struct.pack_into('<I',b,12,63)]
    for offset,value in ((16,0),(24,0),(16,0x60000008),(24,0x50000002),
                         (16,1<<48),(24,1<<48),(32,1),(40,1)):
        malformed.append(lambda b,o=offset,v=value:struct.pack_into('<Q',b,o,v))
    for base in (0x100000,0x4000000,0x100000000):
        good=case(raw,base);assert good['status']==1 and good['stopped']=='target';results.append(good)
        for value in (3,12):
            result=case(raw,base,cntkctl=value);assert result['status']==1 and result['stopped']=='target';results.append(result)
        for value in (0x10,0x40,0x80,0xf0):
            result=case(raw,base,cntkctl=value);assert result['status']==5 and result['stopped']=='halt';results.append(result)
        for frequency in (0,24000000,52000000):
            result=case(raw,base,cntfrq=frequency);assert result['status']==5 and result['stopped']=='halt';results.append(result)
        for value in (1,4,0x1000,0x1005):
            result=case(raw,base,sctlr=value);assert result['status']==4 and result['stopped']=='halt';results.append(result)
        for el in (8,12):
            result=case(raw,base,el=el);assert result['status']==2 and result['stopped']=='halt';results.append(result)
        for patch in malformed:
            result=case(raw,base,patch=patch);assert result['status']==3 and result['stopped']=='halt';results.append(result)
    report={'passed':True,'cases':len(results),'elf_sha256':hashlib.sha256(raw).hexdigest(),
            'scope':'Actual instructions; synthetic EL1/EL2/EL3, SCTLR, CNTKCTL/CNTFRQ and DAIF; target branch only',
            'hardware_verified':False,'xnu_executed':False,'deployment_ready':False,'device_operations':[]}
    (binary.parent/'test-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
