"""Reject mutations to v38 prepared layers even when final hashes are changed."""
import argparse,hashlib,json,shutil,tempfile
from pathlib import Path
from pm_branch_binding import validate_prepared

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--artifact',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.artifact);out=Path(a.output);out.mkdir(parents=True,exist_ok=False);build=json.loads((root/'build-result.json').read_text(encoding='utf-8'));validate_prepared(root,build);names=('kernel/note10_pm_pre_chain.c','kernel/power/note10_pm_pre_capture.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','drivers/perf/arm_pmu.c','kernel/power/Kconfig','kernel/note10_pm_branch_chain.c')
 with tempfile.TemporaryDirectory(dir=out) as t:
  work=Path(t);shutil.copytree(root/'pm-preconditions-prepared',work/'pm-preconditions-prepared');shutil.copytree(root/'pm-branch-prepared',work/'pm-branch-prepared')
  for n in names:
   p=work/'pm-branch-prepared'/n;old=p.read_bytes();p.write_bytes(old+b'\n/* altered */\n');bad=json.loads(json.dumps(build));bad['pm_branch_prepared_sha256'][n]=hashlib.sha256(p.read_bytes()).hexdigest()
   try:validate_prepared(work,bad)
   except ValueError:pass
   else:raise AssertionError(n+' accepted')
   p.write_bytes(old)
  p=work/'pm-preconditions-prepared/kernel/cpu_pm.c';p.write_bytes(p.read_bytes()+b'x')
  try:validate_prepared(work,build)
  except ValueError:pass
  else:raise AssertionError('v37 prior changed')
 d={'passed':True,'cases':['baseline','chain','capture','worker','pmu','kconfig','new-helper','v37-prior'],'binding_sha256':hashlib.sha256(Path(__file__).with_name('pm_branch_binding.py').read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(out/'result.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
