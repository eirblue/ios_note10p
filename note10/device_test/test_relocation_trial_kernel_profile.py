"""Only new decoded GPR gate and explicit kernel-profile contract fixtures."""
import argparse
import copy
import json
from pathlib import Path
from relocation_trial_kernel_profile import PROFILE_ID,kernel_profile,verify_profile_report,gpr_only
from relocation_trial_aarch64_model import private_path,sha,write

PREFIX='q0_fp.o:\tfile format elf64-littleaarch64\nDisassembly of section .text:\n0000000000000000 <v31>:\n'
ACCEPT={
 'gpr-arithmetic':'0: 91000400  add x0, x0, #1\n',
 'gpr-register-pair':'0: a94053f3  ldp x19, x20, [sp]\n',
 'misleading-address-encoding':'dc: d8000000  mov x0, x1\n',
 'misleading-symbol-annotation':'0: 14000100  b 0x400 <q0_v31_s2>\n',
}
REJECT={
 'reject-vector-register':'0: 4e228420  add v0.16b, v1.16b, v2.16b\n',
 'reject-fp-pair':'0: 2d7f8da2  ldp s2, s3, [x13, #-4]\n',
 'reject-fp-mnemonic':'0: 9e670000  fmov d0, x0\n',
 'reject-quad-register':'0: 3dc00000  ldr q0, [x0]\n',
 'reject-sve-register':'0: f9400000  ldr z0.s, [x0]\n',
 'reject-malformed-register':'0: f9400000  ldr x99, [x0]\n',
 'reject-unclosed-annotation':'0: 14000100  b 0x400 <q0\n',
 'reject-malformed-row':'0: xyz  mov x0, x1\n',
}
PROFILE_CASES=('explicit-profile','reject-implicit-profile','reject-wrong-profile','reject-changed-flags','reject-FP-enabled-readback')
CASE_INVENTORY=tuple(ACCEPT)+tuple(REJECT)+PROFILE_CASES

def run_cases():
    result=[]
    def check(name,fn,reject=False):
        try:fn()
        except ValueError:
            if not reject:raise
        else:
            if reject:raise AssertionError('invalid GPR/profile fixture admitted: '+name)
        result.append({'name':name,'passed':True})
    for name,row in ACCEPT.items():check(name,lambda row=row:gpr_only(PREFIX+row))
    for name,row in REJECT.items():check(name,lambda row=row:gpr_only(PREFIX+row),True)
    settings=kernel_profile(PROFILE_ID)
    report={'codegen_profile':settings,'emulator':{'fp_advsimd_setting':{'register':'CPACR_EL1','value':0,'model_assumption_only':True},'cpacr_before':0,'cpacr_after':0}}
    check('explicit-profile',lambda:verify_profile_report(report,PROFILE_ID))
    check('reject-implicit-profile',lambda:verify_profile_report(report,None),True)
    check('reject-wrong-profile',lambda:verify_profile_report(report,'unknown'),True)
    changed=copy.deepcopy(report);changed['codegen_profile']['selected_flags'].append('-ffixed-x18')
    check('reject-changed-flags',lambda:verify_profile_report(changed,PROFILE_ID),True)
    changed_fp=copy.deepcopy(report);changed_fp['emulator']['cpacr_after']=3<<20
    check('reject-FP-enabled-readback',lambda:verify_profile_report(changed_fp,PROFILE_ID),True)
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    out=private_path(a.output);out.mkdir(parents=True,exist_ok=False)
    write(out/'result.json',{'schema':1,'fixture_only':True,'synthetic_only':True,'whole_ci_accepted':False,'hardware_verified':False,
      'cases':run_cases(),'source_sha256':{n:sha(Path(__file__).parent/n) for n in ('relocation_trial_kernel_profile.py','relocation_trial_kernel_profile.json','test_relocation_trial_kernel_profile.py')}})
