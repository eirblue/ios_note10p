"""Reject v44 RCU context source, configuration and model evidence mutations."""
import argparse,hashlib,json,shutil,tempfile
from pathlib import Path
from rcu_context_binding import validate_core
CASES=('source-map-omitted','snapshot-map-omitted','version-omitted','prior-source-changed','final-source-changed','generated-source-changed','coherent-generated-change','case-omitted','config-disabled','image-marker-missing','package-map-missing','collector-map-missing','collector-proof-changed','preempt-rcu-disabled','pinned-header-changed')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--artifact',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();artifact=Path(a.artifact);out=Path(a.output);out.mkdir(parents=True,exist_ok=False);base=json.loads((artifact/'build-result.json').read_text(encoding='utf8'))
 with tempfile.TemporaryDirectory() as t:
  root=Path(t)
  for n in ('pm-preconditions-prepared','pm-branch-prepared','pmu-failure-prepared','pmu-failure-model','pmu-failure-binding-model','pmu-failure-package-flow-model','gic-priority-prepared','gic-priority-model','gic-priority-binding-model','gic-priority-package-flow-model','pmu-state-prepared','pmu-state-native-model','pmu-state-final-lifecycle-model','pmu-state-worker-model','pmu-state-collector-model','pmu-state-binding-model','pmu-state-package-flow-model','pmu-control-prepared','pmu-control-native-model','pmu-control-final-lifecycle-model','pmu-control-worker-model','pmu-control-collector-model','pmu-control-binding-model','pmu-control-package-flow-model','fpsimd-reference-prepared','fpsimd-reference-native-model','fpsimd-reference-final-lifecycle-model','fpsimd-reference-worker-model','fpsimd-reference-decoder-model','fpsimd-reference-collector-model','fpsimd-reference-binding-model','fpsimd-reference-package-flow-model','rcu-context-prepared','rcu-context-native-model','rcu-context-final-lifecycle-model','rcu-context-worker-model','rcu-context-decoder-model','rcu-context-collector-model'):shutil.copytree(artifact/n,root/n)
  for n in ('Image','handoff.config'):shutil.copyfile(artifact/n,root/n)
  validate_core(root,base)
  for case in CASES:
   b=dict(base);changes=[]
   if case in ('source-map-omitted','snapshot-map-omitted','version-omitted','package-map-missing','collector-map-missing'):
    b.pop({'source-map-omitted':'rcu_context_sources_sha256','snapshot-map-omitted':'rcu_context_snapshot_sha256','version-omitted':'rcu_context_audit_version','package-map-missing':'rcu_context_package_sources_sha256','collector-map-missing':'rcu_context_collector_dependencies_sha256'}[case])
   else:
    p=root/{'prior-source-changed':'fpsimd-reference-prepared/arch/arm64/kernel/fpsimd.c','final-source-changed':'rcu-context-prepared/kernel/rcu/tree.c','generated-source-changed':'rcu-context-worker-model/enabled.c','coherent-generated-change':'rcu-context-worker-model/enabled.c','case-omitted':'rcu-context-worker-model/result.json','config-disabled':'handoff.config','image-marker-missing':'Image','unsupported-max-gic':'handoff.config','nonbanked':'handoff.config','collector-proof-changed':'rcu-context-collector-model/result.json','preempt-rcu-disabled':'handoff.config','pinned-header-changed':'rcu-context-prepared/kernel/rcu/tree.h'}[case];raw=p.read_bytes();changes.append((p,raw))
    if case=='case-omitted':m=json.loads(raw);m['cases'].pop();p.write_text(json.dumps(m),encoding='utf8')
    elif case=='collector-proof-changed':m=json.loads(raw);m['dependencies_sha256'].pop(next(iter(m['dependencies_sha256'])));p.write_text(json.dumps(m),encoding='utf8')
    elif case=='config-disabled':p.write_bytes(raw.replace(b'CONFIG_NOTE10_RCU_CONTEXT_AUDIT=y',b'# CONFIG_NOTE10_RCU_CONTEXT_AUDIT is not set'))
    elif case=='preempt-rcu-disabled':p.write_bytes(raw.replace(b'CONFIG_PREEMPT_RCU=y',b'# CONFIG_PREEMPT_RCU is not set'))
    elif case=='image-marker-missing':p.write_bytes(raw.replace(b'N10RCM1',b'N10RCx1'))
    else:
     p.write_bytes(raw+b'\nmutation\n')
     if case=='coherent-generated-change':
      q=root/'rcu-context-worker-model/result.json';old=q.read_bytes();changes.append((q,old));m=json.loads(old);m['generated_sha256']['enabled.c']=hashlib.sha256(p.read_bytes()).hexdigest();q.write_text(json.dumps(m),encoding='utf8')
   try:validate_core(root,b)
   except (ValueError,KeyError,FileNotFoundError):pass
   else:raise RuntimeError('accepted mutation: '+case)
   finally:
    for p,raw in changes:p.write_bytes(raw)
 result={'passed':True,'cases':list(CASES),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
