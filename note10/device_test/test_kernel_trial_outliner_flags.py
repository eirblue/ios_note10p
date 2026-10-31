"""Only new explicit backend-option and reachable anonymous-helper fixtures."""
import argparse
from pathlib import Path
from kernel_trial_object import component_closure
from test_kernel_trial_component import synthetic_object
from relocation_trial_aarch64_model import private_path,sha,write

CASE_INVENTORY=('outliner-never-exact','missing-outliner-control-rejected','unpaired-outliner-control-rejected',
 'duplicate-outliner-control-rejected','later-conflicting-outliner-control-rejected','combined-outliner-token-rejected','reachable-machine-outline-rejected')

def run_cases(option_validator):
    rows=[]
    def check(name,fn,reject=False):
        try:fn()
        except ValueError:
            if not reject:raise
        else:
            if reject:raise AssertionError('invalid analysis flag/helper fixture admitted: '+name)
        rows.append({'name':name,'passed':True})
    pair=['clang-14','-Oz','-mllvm','-enable-machine-outliner=never','-c','init.c']
    check('outliner-never-exact',lambda:option_validator(pair))
    check('missing-outliner-control-rejected',lambda:option_validator(['clang-14','-Oz','-c','init.c']),True)
    check('unpaired-outliner-control-rejected',lambda:option_validator(['clang-14','-enable-machine-outliner=never','-c','init.c']),True)
    check('duplicate-outliner-control-rejected',lambda:option_validator(pair+['-mllvm','-enable-machine-outliner=never']),True)
    check('later-conflicting-outliner-control-rejected',lambda:option_validator(pair+['-mllvm','-enable-machine-outliner=always']),True)
    check('combined-outliner-token-rejected',lambda:option_validator(['clang-14','-mllvm=-enable-machine-outliner=never']),True)
    obj=synthetic_object();index=len(obj['sections']);obj['sections'].append({'index':index,'name':'.text.OUTLINED_FUNCTION_0','flags':6,'bytes':b'\0'*4})
    symbol={'name':'OUTLINED_FUNCTION_0','section':index,'value':0,'size':4,'info':2};obj['symbols'].append(symbol)
    obj['relocations'].append({'section':4,'offset':0,'type':283,'addend':0,'symbol':symbol})
    check('reachable-machine-outline-rejected',lambda:component_closure(obj),True)
    return rows

if __name__=='__main__':
    from build_kernel_trial_component import validate_outliner_options
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();out=private_path(a.output);out.mkdir(parents=True,exist_ok=False)
    write(out/'result.json',{'schema':1,'fixture_only':True,'synthetic_only':True,'whole_ci_accepted':False,'hardware_verified':False,
      'old28_public_or10_private_replayed':False,'cases':run_cases(validate_outliner_options),'source_sha256':{name:sha(Path(__file__).parent/name) for name in ('build_kernel_trial_component.py','test_kernel_trial_outliner_flags.py','kernel_trial_object.py')}})
