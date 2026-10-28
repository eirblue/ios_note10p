"""Reject omissions and scope downgrade in the complete proof fixture."""
import argparse,hashlib,json,shutil,tempfile
from pathlib import Path
from pm_preconditions_binding import validate_model

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--artifact',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.artifact);o=Path(a.output);o.mkdir(parents=True,exist_ok=False);build=json.loads((root/'build-result.json').read_text(encoding='utf-8'));assert validate_model(root,build,False);cases=['metadata-downgrade','config-downgrade','image-marker-omission','model-source-omission','model-case-omission','proof-file-omission']
 with tempfile.TemporaryDirectory(dir=o) as temp:
  for case in cases:
   p=Path(temp)/case;p.mkdir();b=json.loads(json.dumps(build))
   for n in ('Image','handoff.config'):shutil.copyfile(root/n,p/n)
   for n in ('pm-preconditions-prepared','pm-preconditions-getters-model','pm-preconditions-gic-model','pm-preconditions-lifecycle-model','pm-preconditions-producer-model','pm-preconditions-caller-model','pm-preconditions-worker-model'):
    shutil.copytree(root/n,p/n,ignore=shutil.ignore_patterns('*.exe'))
   (p/'pm-preconditions-binding-model').mkdir();shutil.copyfile(root/'pm-preconditions-binding-model/result.json',p/'pm-preconditions-binding-model/result.json')
   if case=='metadata-downgrade':b['pm_preconditions_diagnostic']=False
   if case=='config-downgrade':(p/'handoff.config').write_bytes((p/'handoff.config').read_bytes().replace(b'CONFIG_NOTE10_CPU_PM_PRECONDITIONS=y',b'# CONFIG_NOTE10_CPU_PM_PRECONDITIONS is not set'))
   if case=='image-marker-omission':(p/'Image').write_bytes((p/'Image').read_bytes().replace(b'N10PRR1',b'N10PRXX'))
   if case.startswith('model-'):
    f=p/'pm-preconditions-gic-model/result.json';x=json.loads(f.read_text());x.pop('source_sha256' if case=='model-source-omission' else 'cases');f.write_text(json.dumps(x))
   if case=='proof-file-omission':(p/'pm-preconditions-worker-model/worker.c').unlink()
   try:validate_model(p,b,False)
   except (ValueError,FileNotFoundError):continue
   raise AssertionError(case+' accepted')
 result={'passed':True,'cases':['baseline']+cases,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(o/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
