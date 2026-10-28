"""Create the prior v41 active fixture with only v42 disabled."""
import json,shutil
from pathlib import Path

def prepare(source,destination):
 source=Path(source);destination=Path(destination)
 if destination.exists():raise ValueError('fixture already exists')
 destination.mkdir(parents=True)
 names=('pm-preconditions-prepared','pm-branch-prepared','pmu-failure-prepared','pmu-failure-model','pmu-failure-binding-model','pmu-failure-package-flow-model','gic-priority-prepared','gic-priority-model','gic-priority-binding-model','gic-priority-package-flow-model','pmu-state-prepared','pmu-state-native-model','pmu-state-final-lifecycle-model','pmu-state-worker-model','pmu-state-collector-model','pmu-state-binding-model')
 for n in names:
  if n in ('pmu-failure-package-flow-model','gic-priority-binding-model','gic-priority-package-flow-model','pmu-state-binding-model') and not (source/n).exists():continue
  shutil.copytree(source/n,destination/n)
 config=(source/'handoff.config').read_bytes();line=b'CONFIG_NOTE10_PMU_CONTROL_AUDIT=y'
 if config.splitlines().count(line)!=1:raise ValueError('state flag missing from input')
 (destination/'handoff.config').write_bytes(config.replace(line,b'# CONFIG_NOTE10_PMU_CONTROL_AUDIT is not set'))
 build=json.loads((source/'build-result.json').read_text(encoding='utf8'));build={k:v for k,v in build.items() if not k.startswith('pmu_control_')}
 (destination/'build-result.json').write_text(json.dumps(build,indent=2)+'\n',encoding='utf8',newline='\n')
 return destination
