"""Build a v44-shaped package-flow fixture from the v45 offline artifact."""
import hashlib,json,shutil
from pathlib import Path

KEEP=('pm-preconditions-prepared','pm-branch-prepared','pmu-failure-prepared','pmu-failure-model','pmu-failure-binding-model','pmu-failure-package-flow-model','gic-priority-prepared','gic-priority-model','gic-priority-binding-model','gic-priority-package-flow-model','pmu-state-prepared','pmu-state-native-model','pmu-state-final-lifecycle-model','pmu-state-worker-model','pmu-state-collector-model','pmu-state-binding-model','pmu-state-package-flow-model','pmu-control-prepared','pmu-control-native-model','pmu-control-final-lifecycle-model','pmu-control-worker-model','pmu-control-collector-model','pmu-control-binding-model','pmu-control-package-flow-model','fpsimd-reference-prepared','fpsimd-reference-native-model','fpsimd-reference-final-lifecycle-model','fpsimd-reference-worker-model','fpsimd-reference-decoder-model','fpsimd-reference-collector-model','fpsimd-reference-binding-model','fpsimd-reference-package-flow-model','rcu-context-prepared','rcu-context-native-model','rcu-context-final-lifecycle-model','rcu-context-worker-model','rcu-context-decoder-model','rcu-context-collector-model','rcu-context-binding-model')

def prepare(source,destination):
 source,destination=Path(source),Path(destination)
 if destination.exists():raise ValueError('v44 compatibility destination exists')
 destination.mkdir(parents=True)
 for name in KEEP:
  if name.endswith(('-binding-model','-package-flow-model')) and not (source/name).exists():continue
  if not (source/name).is_dir():raise ValueError('required v44 compatibility input missing: '+name)
  shutil.copytree(source/name,destination/name)
 for name in ('handoff.config','Image'):
  shutil.copyfile(source/name,destination/name)
 config=destination/'handoff.config';raw=config.read_bytes();flag=b'CONFIG_NOTE10_EHLD_LOCK_AUDIT=y'
 if raw.splitlines().count(flag)!=1:raise ValueError('v45 EHLD profile flag missing')
 raw=raw.replace(flag,b'# CONFIG_NOTE10_EHLD_LOCK_AUDIT is not set');config.write_bytes(raw)
 image=destination/'Image';raw=image.read_bytes().replace(b'N10ELM1',b'N10ELx1').replace(b'N10ELQ1',b'N10ELx1');image.write_bytes(raw)
 build=json.loads((source/'build-result.json').read_text(encoding='utf8'))
 build={k:v for k,v in build.items() if not k.startswith('ehld_lock_')}
 build['image_sha256']=hashlib.sha256(raw).hexdigest();build['image_size']=len(raw);build['effective_config_sha256']=hashlib.sha256(config.read_bytes()).hexdigest()
 from rcu_context_binding import PACKAGE_SOURCES
 build['rcu_context_package_sources_sha256']={name:hashlib.sha256((Path(__file__).resolve().parent/name).read_bytes()).hexdigest() for name in PACKAGE_SOURCES}
 (destination/'build-result.json').write_text(json.dumps(build,indent=2)+'\n',encoding='utf8',newline='\n')
 return destination
