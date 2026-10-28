"""Make a guarded-off prior-feature fixture for the immutable v39 flow test."""
import json,shutil
from pathlib import Path

def prepare(source,destination):
 source=Path(source);destination=Path(destination)
 if destination.exists():raise ValueError('Compatibility fixture already exists')
 destination.mkdir(parents=True)
 for n in ('pm-preconditions-prepared','pm-branch-prepared','pmu-failure-prepared','pmu-failure-model','pmu-failure-binding-model'):shutil.copytree(source/n,destination/n)
 config=(source/'handoff.config').read_bytes();line=b'CONFIG_NOTE10_GIC_PRIORITY_RESTORE=y'
 if config.splitlines().count(line)!=1:raise ValueError('Expected enabled GIC guard in actual input')
 config=config.replace(line,b'# CONFIG_NOTE10_GIC_PRIORITY_RESTORE is not set');(destination/'handoff.config').write_bytes(config)
 build=json.loads((source/'build-result.json').read_text(encoding='utf8'));build={k:v for k,v in build.items() if not k.startswith('gic_priority_')}
 (destination/'build-result.json').write_text(json.dumps(build,indent=2)+'\n',encoding='utf8')
 return destination
