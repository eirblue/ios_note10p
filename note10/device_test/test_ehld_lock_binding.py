"""Reject altered v45 composition, instrumentation profile, and model evidence."""
import argparse,hashlib,json,shutil,tempfile
from pathlib import Path
from ehld_lock_binding import validate_core

CASES=('source-map-omitted','snapshot-map-omitted','version-omitted','profile-result-omitted','profile-pin-snapshot-mutated','prepared-source-mutated','coherent-final-source-map-mutated','image-marker-missing','config-disabled','package-map-omitted','collector-map-omitted','collector-proof-mutated','collector-harness-mutated','native-generated-mutated','native-generated-coherent-mutated','lifecycle-case-omitted','worker-generated-coherent-mutated','decoder-case-omitted','profile-proof-mutated','disabled-artifact-downgrade')
DIRS=('pm-preconditions-prepared','pm-branch-prepared','pmu-failure-prepared','pmu-failure-model','pmu-failure-binding-model','pmu-failure-package-flow-model','gic-priority-prepared','gic-priority-model','gic-priority-binding-model','gic-priority-package-flow-model','pmu-state-prepared','pmu-state-native-model','pmu-state-final-lifecycle-model','pmu-state-worker-model','pmu-state-collector-model','pmu-state-binding-model','pmu-state-package-flow-model','pmu-control-prepared','pmu-control-native-model','pmu-control-final-lifecycle-model','pmu-control-worker-model','pmu-control-collector-model','pmu-control-binding-model','pmu-control-package-flow-model','fpsimd-reference-prepared','fpsimd-reference-native-model','fpsimd-reference-final-lifecycle-model','fpsimd-reference-worker-model','fpsimd-reference-decoder-model','fpsimd-reference-collector-model','fpsimd-reference-binding-model','fpsimd-reference-package-flow-model','rcu-context-prepared','rcu-context-native-model','rcu-context-final-lifecycle-model','rcu-context-worker-model','rcu-context-decoder-model','rcu-context-collector-model','rcu-context-binding-model','ehld-lock-prepared','ehld-lock-profile-inputs','ehld-lock-profile-model','ehld-lock-composition-model','ehld-lock-native-model','ehld-lock-final-lifecycle-model','ehld-lock-worker-model','ehld-lock-decoder-model','ehld-lock-collector-model')

def main():
 p=argparse.ArgumentParser();p.add_argument('--artifact',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();artifact,out=a.artifact,a.output;out.mkdir(parents=True,exist_ok=False)
 base=json.loads((artifact/'build-result.json').read_text(encoding='utf8'))
 with tempfile.TemporaryDirectory() as temp:
  root=Path(temp)
  for name in DIRS:shutil.copytree(artifact/name,root/name)
  for name in ('Image','handoff.config'):shutil.copyfile(artifact/name,root/name)
  validate_core(root,base)
  for case in CASES:
   b=json.loads(json.dumps(base));restore=[]
   if case in ('source-map-omitted','snapshot-map-omitted','version-omitted','profile-result-omitted','package-map-omitted','collector-map-omitted'):
    key={'source-map-omitted':'ehld_lock_sources_sha256','snapshot-map-omitted':'ehld_lock_snapshot_sha256','version-omitted':'ehld_lock_audit_version','profile-result-omitted':'ehld_lock_profile_result','package-map-omitted':'ehld_lock_package_sources_sha256','collector-map-omitted':'ehld_lock_collector_dependencies_sha256'}[case];b.pop(key)
   else:
    rel={'profile-pin-snapshot-mutated':'ehld-lock-profile-inputs/arch/Kconfig','prepared-source-mutated':'ehld-lock-prepared/kernel/power/note10_ehld_lock_capture.c','coherent-final-source-map-mutated':'ehld-lock-prepared/kernel/note10_pm_pre_chain.c','image-marker-missing':'Image','config-disabled':'handoff.config','collector-proof-mutated':'ehld-lock-collector-model/result.json','collector-harness-mutated':'ehld-lock-collector-model/result.json','native-generated-mutated':'ehld-lock-native-model/model.c','native-generated-coherent-mutated':'ehld-lock-native-model/model.c','lifecycle-case-omitted':'ehld-lock-final-lifecycle-model/result.json','worker-generated-coherent-mutated':'ehld-lock-worker-model/enabled.c','decoder-case-omitted':'ehld-lock-decoder-model/result.json','profile-proof-mutated':'ehld-lock-profile-model/result.json','disabled-artifact-downgrade':'Image'}[case]
    target=root/rel;old=target.read_bytes();restore.append((target,old));target.write_bytes(old+b'\nmutation\n')
    if case=='coherent-final-source-map-mutated':
     digest=hashlib.sha256(target.read_bytes()).hexdigest();b['ehld_lock_snapshot_sha256']['kernel/note10_pm_pre_chain.c']=digest;b['ehld_lock_prepared_sha256']['kernel/note10_pm_pre_chain.c']=digest
    elif case=='image-marker-missing':target.write_bytes(old.replace(b'N10ELM1',b'N10ELx1',1))
    elif case=='config-disabled':target.write_bytes(old.replace(b'CONFIG_NOTE10_EHLD_LOCK_AUDIT=y',b'# CONFIG_NOTE10_EHLD_LOCK_AUDIT is not set',1))
    elif case=='collector-proof-mutated':
     proof=json.loads(old);proof['dependencies_sha256'].pop(next(iter(proof['dependencies_sha256'])));target.write_text(json.dumps(proof),encoding='utf8')
    elif case=='collector-harness-mutated':
     proof=json.loads(old);proof['harness_sha256']='0'*64;target.write_text(json.dumps(proof),encoding='utf8')
    elif case=='native-generated-coherent-mutated':
     result=root/'ehld-lock-native-model/result.json';saved=result.read_bytes();restore.append((result,saved));proof=json.loads(saved);proof['generated_sha256']=hashlib.sha256(target.read_bytes()).hexdigest();result.write_text(json.dumps(proof),encoding='utf8')
    elif case=='lifecycle-case-omitted':
     proof=json.loads(old);proof['cases'].pop();target.write_text(json.dumps(proof),encoding='utf8')
    elif case=='worker-generated-coherent-mutated':
     result=root/'ehld-lock-worker-model/result.json';saved=result.read_bytes();restore.append((result,saved));proof=json.loads(saved);proof['generated_sha256']['enabled.c']=hashlib.sha256(target.read_bytes()).hexdigest();result.write_text(json.dumps(proof),encoding='utf8')
    elif case=='decoder-case-omitted':
     proof=json.loads(old);proof['cases'].pop();target.write_text(json.dumps(proof),encoding='utf8')
    elif case=='profile-proof-mutated':
     proof=json.loads(old);proof['pins'].pop(next(iter(proof['pins'])));target.write_text(json.dumps(proof),encoding='utf8')
    elif case=='disabled-artifact-downgrade':
     target.write_bytes(old.replace(b'N10ELM1',b'N10ELx1').replace(b'N10ELQ1',b'N10ELx1'))
     cfg=root/'handoff.config';cfgold=cfg.read_bytes();restore.append((cfg,cfgold));cfg.write_bytes(cfgold.replace(b'CONFIG_NOTE10_EHLD_LOCK_AUDIT=y',b'# CONFIG_NOTE10_EHLD_LOCK_AUDIT is not set'))
     b={k:v for k,v in b.items() if not k.startswith('ehld_lock_')};b['ehld_lock_audit']=False;b['ehld_lock_audit_version']=None
   try:
    try:validate_core(root,b)
    except (ValueError,KeyError,FileNotFoundError,TypeError):pass
    else:raise RuntimeError('accepted mutation: '+case)
   finally:
    for path,raw in reversed(restore):path.write_bytes(raw)
 result={'passed':True,'hardware_verified':False,'cases':list(CASES),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
