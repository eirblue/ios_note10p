"""Reject v38 scope, model metadata and proof omissions."""
import argparse,hashlib,json,shutil,tempfile
from pathlib import Path
from pm_branch_binding import validate_core

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--artifact',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.artifact);out=Path(a.output);out.mkdir(parents=True,exist_ok=False);build=json.loads((root/'build-result.json').read_text(encoding='utf-8'));assert validate_core(root,build)
 cases=('metadata','config','marker','source','cases','proof')
 with tempfile.TemporaryDirectory(dir=out) as temp:
  for case in cases:
   p=Path(temp)/case;p.mkdir();b=json.loads(json.dumps(build))
   for n in ('Image','handoff.config'):shutil.copyfile(root/n,p/n)
   for src in root.glob('pm-preconditions-*'):
    if not src.is_dir():continue
    if src.name in ('pm-preconditions-binding-model','pm-preconditions-scope-model'):
     (p/src.name).mkdir();shutil.copyfile(src/'result.json',p/src.name/'result.json')
    else:shutil.copytree(src,p/src.name,ignore=shutil.ignore_patterns('*.exe'))
   for src in root.glob('pm-branch-*'):
    if not src.is_dir() or src.name=='pm-branch-scope-model':continue
    if src.name=='pm-branch-binding-model':
     (p/src.name).mkdir();shutil.copyfile(src/'result.json',p/src.name/'result.json')
    else:shutil.copytree(src,p/src.name,ignore=shutil.ignore_patterns('*.exe'))
   if case=='metadata':b.pop('pm_branch_diagnostic')
   if case=='config':(p/'handoff.config').write_bytes((p/'handoff.config').read_bytes().replace(b'CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT=y',b'# CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT is not set'))
   if case=='marker':(p/'Image').write_bytes((p/'Image').read_bytes().replace(b'N10BRAR1',b'XXXXXXXX'))
   if case in ('source','cases'):
    f=p/'pm-branch-native-model/result.json';d=json.loads(f.read_text());d.pop('source_sha256' if case=='source' else 'cases');f.write_text(json.dumps(d))
   if case=='proof':(p/'pm-branch-worker-model/enabled.c').unlink()
   try:validate_core(p,b)
   except (ValueError,FileNotFoundError,KeyError):continue
   raise AssertionError(case+' accepted')
 d={'passed':True,'cases':['baseline',*cases],'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(out/'result.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
