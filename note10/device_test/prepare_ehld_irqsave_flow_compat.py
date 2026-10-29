"""Remove v46-only scope from a private copy before replaying older flows."""
import hashlib,json,shutil
from pathlib import Path

DROP_DIRS={'ehld-irqsave-prepared','ehld-irqsave-model','ehld-irqsave-binding-model','ehld-irqsave-package-flow-model'}
MODEL_PREFIXES=('abox-','auto-','cpu-','dma-','ehld-','fpsimd-','gic-','iommu-','pm-','pmu-','rcu-','ufs-')
KEEP_FILES={'Image','handoff.config','build-result.json','initramfs.cpio','minimal-init.elf','minimal-init-model.json','pm-callbacks-binding-input.json','pm-source-model.json','public-baseline.config'}
def prepare(source,destination):
 source,destination=Path(source),Path(destination)
 if source.is_symlink() or not source.is_dir() or destination.exists() or destination.is_symlink():raise ValueError('invalid v45 compatibility paths')
 cfg=(source/'handoff.config').read_bytes();flag=b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=y'
 if cfg.splitlines().count(flag)!=1:raise ValueError('v46 irqsave option is not uniquely enabled')
 cfg=cfg.replace(flag,b'# CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT is not set')
 report=json.loads((source/'build-result.json').read_text(encoding='utf8'))
 if report.get('ehld_irqsave_audit') is not True:raise ValueError('v46 irqsave package scope is not enabled')
 report={k:v for k,v in report.items() if not k.startswith('ehld_irqsave_')}
 if not isinstance(report.get('ehld_lock_profile_result'),dict):raise ValueError('v45 EHLD measured profile proof missing')
 from ehld_lock_profile import verify_config
 profile=verify_config(cfg)
 report['ehld_lock_profile_result']=profile
 from ehld_lock_binding import SOURCES as EHLD_SOURCES,PACKAGE_SOURCES as EHLD_PACKAGES,COLLECTOR_DEPENDENCIES
 from rcu_context_binding import SOURCES as RCU_SOURCES,PACKAGE_SOURCES as RCU_PACKAGES
 from rcu_context_binding import COLLECTOR_DEPENDENCIES as RCU_COLLECTOR
 base=Path(__file__).resolve().parent
 digest=lambda name:hashlib.sha256((base/name).read_bytes()).hexdigest()
 report['ehld_lock_sources_sha256']={name:digest(name) for name in EHLD_SOURCES}
 report['ehld_lock_package_sources_sha256']={name:digest(name) for name in EHLD_PACKAGES}
 report['ehld_lock_collector_dependencies_sha256']={name:digest(name) for name in COLLECTOR_DEPENDENCIES}
 report['rcu_context_sources_sha256']={name:digest(name) for name in RCU_SOURCES}
 report['rcu_context_package_sources_sha256']={name:digest(name) for name in RCU_PACKAGES}
 report['rcu_context_collector_dependencies_sha256']={name:digest(name) for name in RCU_COLLECTOR}
 for key,value in list(report.items()):
  if key.endswith('_package_sources_sha256'):
   if not isinstance(value,dict) or any(not isinstance(name,str) for name in value):raise ValueError('invalid historical package source map')
   report[key]={name:digest(name) for name in value}
  elif key.endswith('_collector_dependencies_sha256'):
   if not isinstance(value,dict) or any(not isinstance(name,str) for name in value):raise ValueError('invalid historical collector dependency map')
   report[key]={name:digest(name) for name in value}
 from rcu_context_binding import MARKERS as RCU_MARKERS
 from ehld_lock_binding import MARKERS as EHLD_MARKERS
 image=bytearray(4096);image[56:60]=b'ARM\x64';image[128:]=b''.join(RCU_MARKERS+EHLD_MARKERS)
 image=bytes(image)
 destination.mkdir(parents=True)
 for item in source.iterdir():
  keep_dir=item.is_dir() and item.name.startswith(MODEL_PREFIXES) and item.name not in DROP_DIRS
  keep_file=item.is_file() and item.name in KEEP_FILES
  if not (keep_dir or keep_file):continue
  if item.is_symlink():raise ValueError('symlink in v45 compatibility source')
  target=destination/item.name
  if item.is_dir():
   if any(p.is_symlink() for p in item.rglob('*')):raise ValueError('nested symlink in v45 compatibility source')
   shutil.copytree(item,target)
  else:shutil.copy2(item,target)
 (destination/'handoff.config').write_bytes(cfg)
 (destination/'Image').write_bytes(image)
 report.update(build_passed=False,compatibility_model_only=True,hardware_verified=False,
               image_sha256=hashlib.sha256(image).hexdigest(),image_size=len(image),
               effective_config_sha256=hashlib.sha256(cfg).hexdigest())
 (destination/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
 return destination
