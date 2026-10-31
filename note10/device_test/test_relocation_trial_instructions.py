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
NEW_CLANG14={
 'clang14-ushll':'     4cc: 42 a4 08 2f  \tushll\tv2.8h, v2.8b, #0\n',
 'clang14-sshll':'     4e4: 42 a4 10 0f  \tsshll\tv2.4s, v2.4h, #0\n',
 'clang14-bit':'     504: 20 1c a2 6e  \tbit\tv0.16b, v1.16b, v2.16b\n',
 'clang14-umov':'     510: 0d 3c 06 0e  \tumov\tw13, v0.h[1]\n',
 'clang14-bfi':'     528: b0 01 1f 33  \tbfi\tw16, w13, #1, #1\n',
}
CASE_INVENTORY=tuple(ACCEPT)+tuple(REJECT)+tuple(NEW_CLANG14)
SAVED_CI_DISASSEMBLY_SHA='b0cd6278cfcbe671967e8a5e1f1a6f55a66069da7e7558c29393d4a1e6be11c0'

def run_cases(new_clang14_only=False):
    results=[]
    if not new_clang14_only:
        for name,row in ACCEPT.items():
            classify(PREFIX+row);results.append({'name':name,'passed':True})
        for name,row in REJECT.items():
            try:classify(PREFIX+row)
            except ValueError:results.append({'name':name,'passed':True});continue
            raise AssertionError('invalid instruction fixture admitted: '+name)
    for name,row in NEW_CLANG14.items():
        classify(PREFIX+row);results.append({'name':name,'passed':True})
    return results

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--new-clang14-only',action='store_true',help='Partial five-case delta; old34 are not replayed')
    ap.add_argument('--saved-disassembly',type=Path,help='Read-only exact preserved failed CI41160322285 disassembly')
    a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    result={'schema':1,'fixture_only':True,'hardware_verified':False,'whole_ci_accepted':False,'cases':run_cases(a.new_clang14_only),
      'partial':a.new_clang14_only,'canonical_case_count':len(CASE_INVENTORY),'canonical_case_inventory':CASE_INVENTORY,
      'selected_case_count':5 if a.new_clang14_only else len(CASE_INVENTORY),
      'execution_limit':'PC code-generation classification only; AdvSIMD can trap when FP access is disabled; no kernel/EL1 readiness or AArch64 execution proof',
      'sources_sha256':{n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in ('relocation_trial_instructions.py','test_relocation_trial_instructions.py')}}
    if a.saved_disassembly:
        expected=Path(__file__).resolve().parents[2]/'note10/private/cloud-runs/41160322285/note10-relocation-trial-pc-only/v58-ci-trial/production-disassembly.log'
        raw=a.saved_disassembly.read_bytes()
        if a.saved_disassembly.resolve()!=expected or hashlib.sha256(raw).hexdigest()!=SAVED_CI_DISASSEMBLY_SHA:raise ValueError('exact retained failed CI disassembly required')
        result['saved_disassembly']={'path':str(expected),'sha256':SAVED_CI_DISASSEMBLY_SHA,
          'classification':classify(raw.decode('utf-8')),'source_run':41160322285,'original_ci_conclusion':'failure',
          'read_only_analysis':True,'compiler_or_native_executed':False,'retroactive_ci_acceptance':False}
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
