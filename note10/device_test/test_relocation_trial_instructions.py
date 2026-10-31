"""New instruction classifier fixtures only; no compiler, device or API."""
import argparse
import hashlib
import json
from pathlib import Path
from relocation_trial_instructions import classify

PREFIX='C:/pc/dc/msr.o:\tfile format elf64-littleaarch64\n\nDisassembly of section .text:\n\n0000000000000000 <dc>:\n'
ACCEPT={
 'address-dc-llvm23':'      dc: 54fffb43  b.lo 0x44 <dc+0x44>\n',
 'address-dc-llvm14':'      dc: 43 fb ff 54  b.lo 0x44 <dc+0x44>\n',
 'hex-encoding-dc':'       0: dc000000  mov x0, x1\n',
 'label-path-privileged-words':'       0: d65f03c0  ret\n',
 'ordinary-arithmetic':'       0: 910003fd  mov x29, sp\n       4: 91000400  add x0, x0, #1\n',
}
REJECT={name:f'       0: d4000000  {name} #0\n' for name in
 ('dc','ic','msr','mrs','sys','sysl','tlbi','at','svc','hvc','smc','eret','drps','wfi','wfe','sev','sevl','hlt','brk')}
REJECT.update({'unknown':'       0: 00000000  <unknown>\n','word':'       0: 00000000  .word 0\n',
 'malformed-encoding':'       0: 1234567  add x0, x0, #1\n','missing-mnemonic':'       0: 12345678\n',
 'unapproved-mnemonic':'       0: 12345678  invented x0\n','missing-operands':'       0: 12345678  add\n',
 'unaligned-address':'       1: d65f03c0  ret\n','duplicate-address':'       0: d65f03c0  ret\n       0: d65f03c0  ret\n',
 'empty':'','malformed-row':'unexpected log text\n'})
CASE_INVENTORY=tuple(ACCEPT)+tuple(REJECT)

def run_cases():
    results=[]
    for name,row in ACCEPT.items():
        classify(PREFIX+row);results.append({'name':name,'passed':True})
    for name,row in REJECT.items():
        try:classify(PREFIX+row)
        except ValueError:results.append({'name':name,'passed':True});continue
        raise AssertionError('invalid instruction fixture admitted: '+name)
    return results

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    result={'schema':1,'fixture_only':True,'hardware_verified':False,'whole_ci_accepted':False,'cases':run_cases(),
      'sources_sha256':{n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in ('relocation_trial_instructions.py','test_relocation_trial_instructions.py')}}
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
