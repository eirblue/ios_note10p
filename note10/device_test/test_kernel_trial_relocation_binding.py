"""Only new exact linked target-section/location/addend mutation fixtures."""
import argparse
import copy
from pathlib import Path
from kernel_trial_object import validate_linked_relocation
from relocation_trial_aarch64_model import private_path,sha,write

CASE_INVENTORY=('linked-relocation-exact','reject-compensating-symbol-addend',
 'reject-linked-target-section','reject-linked-target-location')

def run_cases():
    original={'offset':4,'type':277,'addend':12,'symbol':{'section':1,'value':8}}
    correct={'offset':4,'type':277,'addend':12,'symbol':{'section':3,'value':0x10001008}}
    results=[]
    for name in CASE_INVENTORY:
        linked=copy.deepcopy(correct)
        if name=='reject-compensating-symbol-addend':linked['symbol']['value']+=4;linked['addend']-=4
        if name=='reject-linked-target-section':linked['symbol']['section']=7
        if name=='reject-linked-target-location':linked['symbol']['value']+=4
        try:validate_linked_relocation(original,linked,3,0x10001008)
        except ValueError:
            if name=='linked-relocation-exact':raise
        else:
            if name!='linked-relocation-exact':raise AssertionError('invalid linked relocation identity accepted: '+name)
        results.append({'name':name,'passed':True})
    return results

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();out=private_path(a.output);out.mkdir(parents=True,exist_ok=False)
    write(out/'result.json',{'schema':1,'fixture_only':True,'synthetic_only':True,'whole_ci_accepted':False,'hardware_verified':False,
      'old24_or_private6_replayed':False,'cases':run_cases(),'source_sha256':{name:sha(Path(__file__).parent/name) for name in ('kernel_trial_object.py','test_kernel_trial_relocation_binding.py')}})
