"""Focused wheel-header parsing fixtures; no target code or Unicorn execution."""
import argparse
import hashlib
import json
from pathlib import Path
from relocation_trial_aarch64_model import wheel_metadata,private_path

CASE_INVENTORY=('metadata-lf','metadata-crlf','metadata-wrong-name','metadata-wrong-version',
 'metadata-missing-name','metadata-missing-version','metadata-duplicate-name','metadata-duplicate-version')
BASE=b'Metadata-Version: 2.1\nName: unicorn\nVersion: 2.1.4\n\nDescription\n'

def run_cases():
    inputs={
      'metadata-lf':BASE,'metadata-crlf':BASE.replace(b'\n',b'\r\n'),
      'metadata-wrong-name':BASE.replace(b'Name: unicorn',b'Name: other'),
      'metadata-wrong-version':BASE.replace(b'Version: 2.1.4',b'Version: 2.1.3'),
      'metadata-missing-name':BASE.replace(b'Name: unicorn\n',b''),
      'metadata-missing-version':BASE.replace(b'Version: 2.1.4\n',b''),
      'metadata-duplicate-name':BASE.replace(b'Name: unicorn\n',b'Name: unicorn\nnAmE: unicorn\n'),
      'metadata-duplicate-version':BASE.replace(b'Version: 2.1.4\n',b'Version: 2.1.4\nVersion: 2.1.4\n')}
    results=[]
    for name in CASE_INVENTORY:
        try:wheel_metadata(inputs[name])
        except ValueError:
            if name in CASE_INVENTORY[:2]:raise
        else:
            if name not in CASE_INVENTORY[:2]:raise AssertionError('invalid wheel metadata admitted: '+name)
        results.append({'name':name,'passed':True})
    return results

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    out=private_path(a.output);out.mkdir(parents=True,exist_ok=False)
    value={'schema':1,'fixture_only':True,'synthetic_only':True,'whole_ci_accepted':False,'hardware_verified':False,
      'cases':run_cases(),'source_sha256':{n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in ('relocation_trial_aarch64_model.py','test_relocation_trial_wheel_metadata.py')}}
    (out/'result.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
