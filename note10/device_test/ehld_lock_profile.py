"""Pin the supported narrow no-dynamic-probes profile for the v45 experiment."""
import hashlib
import shutil
from pathlib import Path

DISABLE=(
 'KPROBES','KRETPROBES','UPROBES','KPROBE_EVENTS','UPROBE_EVENTS',
 'PROBE_EVENTS','FUNCTION_TRACER','FUNCTION_GRAPH_TRACER','BPF_EVENTS',
)
PRESERVE=(
 'EXYNOS_EHLD','PERF_EVENTS','HW_PERF_EVENTS','ARM_PMU','PREEMPT',
 'PREEMPT_COUNT','PREEMPT_RCU','TRACEPOINTS','EVENT_TRACING','TRACING',
 'FTRACE','DEBUG_SNAPSHOT','DEBUG_SNAPSHOT_PMU',
)
PINS={
 'arch/Kconfig':'be03bf10b5729b39eed0fa08986951d10242a18b772c108a26b91506eb16ad4e',
 'arch/arm64/Kconfig':'127273290ce9e8d337b0f186b576dac0ff3792bcbebffeea2ae49b9c5e99afc6',
 'kernel/trace/Kconfig':'f3bf8f33caa881d49e2565da8d34c70d9cab133f443adf67b601e564c1acd5a2',
 'lib/Kconfig.debug':'332b70cd46949dbc4ffbca3776dbb6b1a490541af9d4d313674bf5168682b355',
 'drivers/soc/samsung/debug/Kconfig':'2aea069115aae49642d7bd31485e72dd6f982130068aa95e4dda5512a984379a',
 'drivers/soc/samsung/debug/Makefile':'65e3dc294b7752721304c1ee0a35da37a5c22cf3083d868a0f1dbcd4b9677a17',
 'include/soc/samsung/exynos-ehld.h':'eddae7002984e341944f8d29a696179a886bf447d9a5fbb7db047208ac195070',
 'kernel/events/Makefile':'66d8091319d0c16f348fdbc2d4d59af34247e96183bd4a226dfdaf6b0388e0ed',
}

def sha(data):return hashlib.sha256(data).hexdigest()

def verify_pins(source):
 source=Path(source)
 actual={name:sha((source/name).read_bytes()) for name in PINS}
 if actual!=PINS:raise ValueError('pinned instrumentation Kconfig/source inputs differ')
 return actual

def states(config):
 raw=Path(config).read_text(encoding='utf8') if isinstance(config,(str,Path)) else bytes(config).decode('utf8')
 result={}
 for line in raw.splitlines():
  if line.startswith('CONFIG_') and '=' in line:
   key,value=line.split('=',1);key=key[7:]
  elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
   key=line[9:-11];value='n'
  else:continue
  if key in result:raise ValueError('duplicate Kconfig symbol: '+key)
  result[key]=value
 return result

def verify_config(config):
 values=states(config)
 active=[name for name in DISABLE if values.get(name) not in (None,'n')]
 if active:raise ValueError('dynamic instrumentation profile remains enabled: '+','.join(active))
 missing=[name for name in PRESERVE if values.get(name)!='y']
 if missing:raise ValueError('required static framework option missing: '+','.join(missing))
 for name in ('NOTE10_EHLD_LOCK_AUDIT','NOTE10_RCU_CONTEXT_AUDIT'):
  if values.get(name)!='y':raise ValueError('audit feature disabled: '+name)
 return {'disabled':list(DISABLE),'preserved':list(PRESERVE),'measured_config_sha256':sha(bytes(config) if isinstance(config,(bytes,bytearray)) else Path(config).read_bytes())}

def apply_profile(source,config,run):
 source=Path(source);config=Path(config)
 pins=verify_pins(source)
 command=[str(source/'scripts/config'),'--file',str(config)]
 for name in DISABLE:command.extend(('--disable',name))
 run(command,'02-ehld-profile.log')
 return pins

def snapshot_profile(source,output):
 source,output=Path(source),Path(output)
 pins=verify_pins(source)
 if output.exists():raise ValueError('EHLD profile source snapshot exists')
 output.mkdir(parents=True)
 for name in PINS:
  dst=output/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,dst)
 copied={name:sha((output/name).read_bytes()) for name in PINS}
 if copied!=pins:raise ValueError('EHLD profile source snapshot differs')
 return copied
