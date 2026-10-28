"""Reject v42 control source, configuration and model evidence mutations."""
import argparse,hashlib,json,shutil,tempfile
from pathlib import Path
from pmu_control_binding import validate_core
CASES=('source-map-omitted','snapshot-map-omitted','version-omitted','prior-source-changed','final-source-changed','generated-source-changed','coherent-generated-change','case-omitted','config-disabled','image-marker-missing','package-map-missing','collector-map-missing','collector-proof-changed')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--artifact',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();artifact=Path(a.artifact);out=Path(a.output);out.mkdir(parents=True,exist_ok=False);base=json.loads((artifact/'build-result.json').read_text(encoding='utf8'))
 with tempfile.TemporaryDirectory() as t:
  root=Path(t)
  for n in ('pm-preconditions-prepared','pm-branch-prepared','pmu-failure-prepared','pmu-failure-model','pmu-failure-binding-model','pmu-failure-package-flow-model','gic-priority-prepared','gic-priority-model','gic-priority-binding-model','gic-priority-package-flow-model','pmu-state-prepared','pmu-state-native-model','pmu-state-final-lifecycle-model','pmu-state-worker-model','pmu-state-collector-model','pmu-state-binding-model','pmu-state-package-flow-model','pmu-control-prepared','pmu-control-native-model','pmu-control-final-lifecycle-model','pmu-control-worker-model','pmu-control-collector-model'):shutil.copytree(artifact/n,root/n)
  for n in ('Image','handoff.config'):shutil.copyfile(artifact/n,root/n)
  validate_core(root,base)
  for case in CASES:
   b=dict(base);changes=[]
   if case in ('source-map-omitted','snapshot-map-omitted','version-omitted','package-map-missing','collector-map-missing'):
    b.pop({'source-map-omitted':'pmu_control_sources_sha256','snapshot-map-omitted':'pmu_control_snapshot_sha256','version-omitted':'pmu_control_audit_version','package-map-missing':'pmu_control_package_sources_sha256','collector-map-missing':'pmu_control_collector_dependencies_sha256'}[case])
   else:
    p=root/{'prior-source-changed':'pmu-state-prepared/drivers/perf/arm_pmu.c','final-source-changed':'pmu-control-prepared/drivers/perf/arm_pmu.c','generated-source-changed':'pmu-control-worker-model/enabled.c','coherent-generated-change':'pmu-control-worker-model/enabled.c','case-omitted':'pmu-control-worker-model/result.json','config-disabled':'handoff.config','image-marker-missing':'Image','unsupported-max-gic':'handoff.config','nonbanked':'handoff.config','collector-proof-changed':'pmu-control-collector-model/result.json'}[case];raw=p.read_bytes();changes.append((p,raw))
    if case=='case-omitted':m=json.loads(raw);m['cases'].pop();p.write_text(json.dumps(m),encoding='utf8')
    elif case=='collector-proof-changed':m=json.loads(raw);m['dependencies_sha256'].pop(next(iter(m['dependencies_sha256'])));p.write_text(json.dumps(m),encoding='utf8')
    elif case=='config-disabled':p.write_bytes(raw.replace(b'CONFIG_NOTE10_PMU_CONTROL_AUDIT=y',b'# CONFIG_NOTE10_PMU_CONTROL_AUDIT is not set'))
    elif case=='image-marker-missing':p.write_bytes(raw.replace(b'N10PCTR1',b'N10PCTx1'))
    else:
     p.write_bytes(raw+b'\nmutation\n')
     if case=='coherent-generated-change':
      q=root/'pmu-control-worker-model/result.json';old=q.read_bytes();changes.append((q,old));m=json.loads(old);m['generated_c_sha256']['enabled.c']=hashlib.sha256(p.read_bytes()).hexdigest();q.write_text(json.dumps(m),encoding='utf8')
   try:validate_core(root,b)
   except (ValueError,KeyError,FileNotFoundError):pass
   else:raise RuntimeError('accepted mutation: '+case)
   finally:
    for p,raw in changes:p.write_bytes(raw)
 result={'passed':True,'cases':list(CASES),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
