"""Exercise actual source routing and both branch models from saved snapshots."""
import argparse,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from build_handoff_kernel import branch_source_path
HERE=Path(__file__).resolve().parent
CASES=('pmu-source','gic-source')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--artifact',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.artifact);out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
 build=json.loads((root/'build-result.json').read_text(encoding='utf8'));results={}
 for model,script,field,path,count in (('pmu-source','test_pm_branch_source_native.py','pm_branch_prepared_sha256','drivers/perf/arm_pmu.c',8),('gic-source','test_pm_branch_gic_source_native.py','pm_preconditions_prepared_sha256','drivers/irqchip/irq-gic.c',4)):
  source=branch_source_path(root,model);digest=hashlib.sha256(source.read_bytes()).hexdigest()
  if digest!=build[field][path]:raise ValueError('Routed source differs from bound snapshot: '+model)
  target=out/model;r=subprocess.run([sys.executable,'-X','utf8',str(HERE/script),'--source',str(source),'--output',str(target)],capture_output=True,timeout=60)
  (out/(model+'.log')).write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(model+' failed: '+r.stderr.decode(errors='replace'))
  report=json.loads((target/'result.json').read_text(encoding='utf8'))
  if report.get('passed') is not True or report.get('source_sha256')!=digest or len(report.get('cases',[]))!=count:raise ValueError('Routed model proof differs: '+model)
  results[model]={'source_sha256':digest,'cases':count,'passed':True}
 try:branch_source_path(root,'unknown')
 except ValueError:pass
 else:raise ValueError('Unknown model accepted')
 with tempfile.TemporaryDirectory(dir=out) as empty:
  for model in CASES:
   try:branch_source_path(empty,model)
   except ValueError:pass
   else:raise ValueError('Missing routed snapshot accepted: '+model)
 data={'passed':True,'hardware_verified':False,'models':results,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(out/'result.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
