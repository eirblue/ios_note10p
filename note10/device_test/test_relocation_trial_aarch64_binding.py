"""Six synthetic instruction/function-PC binding fixtures, no target execution."""
import argparse
import hashlib
import json
from pathlib import Path

CASE_INVENTORY=('scaled-byte-stores','unscaled-byte-stores','reject-first-wide-store',
 'reject-restore-wide-store','reject-first-write-outside-trial','reject-read-outside-trial')

def run_cases(binding_callable):
    results=[]
    for name in CASE_INVENTORY:
        first='strb';restore='strb';first_pc=0x10000000;read_pc=0x10000004;copy_op='strb'
        if name=='unscaled-byte-stores':first=restore='sturb'
        if name=='reject-first-wide-store':first='strh'
        if name=='reject-restore-wide-store':restore='str'
        if name=='reject-first-write-outside-trial':first_pc=0x10000040
        if name=='reject-read-outside-trial':read_pc=0x10000040;copy_op='ldrb'
        text=('synthetic.o:\tfile format elf64-littleaarch64\nDisassembly of section .text:\n'
          '0000000010000000 <n10_rt_trial>:\n'
          f'10000000: 39000012  {first} w18, [x0]\n'
          '10000004: 39400102  ldrb w2, [x8]\n'
          f'10000008: 3800158f  {restore} w15, [x12], #1\n'
          '0000000010000040 <copy>:\n'
          f'10000040: 39000012  {copy_op} w18, [x0]\n')
        image={'symbols':{'n10_rt_trial':{'value':0x10000000,'size':0x20,'info':18,'flags':6},
          'copy':{'value':0x10000040,'size':0x10,'info':2,'flags':6}}}
        reports=[{'case':'actual-payload-success','observer':{'first_tail_write_pc':first_pc,
          'first_tail_read_pc':read_pc,'restore_start_pc':0x10000008}}]
        try:binding_callable(text,image,reports)
        except ValueError:
            if name in CASE_INVENTORY[:2]:raise
        else:
            if name not in CASE_INVENTORY[:2]:raise AssertionError('invalid byte-store/PC binding admitted: '+name)
        results.append({'name':name,'passed':True})
    return results

if __name__=='__main__':
    from relocation_trial_aarch64_model import private_path
    from test_relocation_trial_aarch64 import disassembly_binding
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    out=private_path(a.output);out.mkdir(parents=True,exist_ok=False)
    value={'schema':1,'fixture_only':True,'synthetic_only':True,'hardware_verified':False,'whole_ci_accepted':False,
      'compiler_or_emulator_executed':False,'cases':run_cases(disassembly_binding),
      'source_sha256':{n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in ('test_relocation_trial_aarch64.py','test_relocation_trial_aarch64_binding.py')}}
    (out/'result.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
