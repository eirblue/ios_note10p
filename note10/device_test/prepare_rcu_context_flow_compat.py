"""Create the prior v43 active fixture with only v44 disabled."""
import json,shutil
from pathlib import Path

def prepare(source,destination):
 source=Path(source);destination=Path(destination)
 if destination.exists():raise ValueError('fixture already exists')
 destination.mkdir(parents=True)
 names=('pm-preconditions-prepared','pm-branch-prepared','pmu-failure-prepared','pmu-failure-model','pmu-failure-binding-model','pmu-failure-package-flow-model','gic-priority-prepared','gic-priority-model','gic-priority-binding-model','gic-priority-package-flow-model','pmu-state-prepared','pmu-state-native-model','pmu-state-final-lifecycle-model','pmu-state-worker-model','pmu-state-collector-model','pmu-state-binding-model','pmu-state-package-flow-model','pmu-control-prepared','pmu-control-native-model','pmu-control-final-lifecycle-model','pmu-control-worker-model','pmu-control-collector-model','pmu-control-binding-model','pmu-control-package-flow-model','fpsimd-reference-prepared','fpsimd-reference-native-model','fpsimd-reference-final-lifecycle-model','fpsimd-reference-worker-model','fpsimd-reference-decoder-model','fpsimd-reference-collector-model','fpsimd-reference-binding-model')
 for n in names:
  if n in ('pmu-failure-package-flow-model','gic-priority-binding-model','gic-priority-package-flow-model','pmu-state-binding-model','pmu-state-package-flow-model','pmu-control-binding-model','pmu-control-package-flow-model','fpsimd-reference-binding-model') and not (source/n).exists():continue
  shutil.copytree(source/n,destination/n)
 config=(source/'handoff.config').read_bytes();line=b'CONFIG_NOTE10_RCU_CONTEXT_AUDIT=y'
 if config.splitlines().count(line)!=1:raise ValueError('state flag missing from input')
 (destination/'handoff.config').write_bytes(config.replace(line,b'# CONFIG_NOTE10_RCU_CONTEXT_AUDIT is not set'))
 build=json.loads((source/'build-result.json').read_text(encoding='utf8'));build={k:v for k,v in build.items() if not k.startswith('rcu_context_')}
 (destination/'build-result.json').write_text(json.dumps(build,indent=2)+'\n',encoding='utf8',newline='\n')
 return destination
