"""Exercise prepared-source reverse composition and tamper rejection."""
import argparse,hashlib,json,shutil
from pathlib import Path
from pm_preconditions_binding import validate_prepared

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--artifact',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.artifact);out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
 build=json.loads((root/'build-result.json').read_text(encoding='utf-8'));snapshot=root/'pm-preconditions-prepared';assert validate_prepared(snapshot,build)
 cases=[('original-gic','drivers/irqchip/irq-gic.c'),('prior-cpu','kernel/power/note10_pm_cpus.c'),('helper','kernel/power/note10_pm_pre_capture.c'),('pinned-header','include/linux/timer.h'),('worker','arch/arm64/mm/note10_pm_timer_roundtrip.c')]
 for name,target in cases:
  target_root=out/name;shutil.copytree(snapshot,target_root);p=target_root/target;p.write_bytes(p.read_bytes()+b'\n/* mutation */\n');changed=json.loads(json.dumps(build));changed['pm_preconditions_prepared_sha256'][target]=sha(p)
  try:validate_prepared(target_root,changed)
  except ValueError:continue
  raise AssertionError(name+' accepted')
 for name,target in [('prior-map','kernel/power/note10_pm_noirq.c'),('pin-map','drivers/perf/arm_pmu_platform.c')]:
  changed=json.loads(json.dumps(build));changed['pm_preconditions_intermediate_sha256'][target]='0'*64
  try:validate_prepared(snapshot,changed)
  except ValueError:continue
  raise AssertionError(name+' accepted')
 result={'passed':True,'cases':['baseline']+[x[0] for x in cases]+['prior-map','pin-map'],'binding_sha256':sha(Path(__file__).with_name('pm_preconditions_binding.py')),'harness_sha256':sha(Path(__file__)),'prepared_map_sha256':hashlib.sha256(json.dumps(build['pm_preconditions_prepared_sha256'],sort_keys=True).encode()).hexdigest()};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
