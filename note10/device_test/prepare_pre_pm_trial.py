"""Exact accepted full diagnostic TU source overlay; no old pipeline execution."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'note10/device_test/full_diagnostic_v57'
OPTION='CONFIG_NOTE10_PRE_PM_TRIAL'
NEW=('pre_pm_trial_policy.h','pre_pm_trial_wrapper.c')
TRIAL=('runtime_relocation_trial.c','runtime_relocation_trial.h')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def sources():
 manifest=json.loads((BASE/'manifest.json').read_text());rows=manifest['files']
 require(len(rows)==62 and len({x['installed_path'] for x in rows})==62,'exact62 overlay')
 result={}
 for x in rows:
  name=x['public_source'];require(name.startswith('note10/') and '..' not in Path(name).parts,'public source path')
  raw=(ROOT/name).read_bytes();require(digest(raw)==x['sha256'] and len(raw)==x['bytes'],'pinned overlay bytes: '+name)
  result[x['installed_path']]=raw
 return result
KCONFIG=b'\nconfig NOTE10_PRE_PM_TRIAL\n\tbool "Compile dormant pre-PM restore trial"\n\tdepends on NOTE10_XNU_RUNTIME_SCRATCH && NOTE10_XNU_RUNTIME_OBSERVATION\n\tdefault n\n'
# The two includes remain inside an explicit default-off option.
INCLUDE=b'\n#ifdef CONFIG_NOTE10_PRE_PM_TRIAL\n#include "pre_pm_trial_wrapper.c"\n#include "kernel_trial_stack_oracle.c"\n#endif\n'
def render(identifier):
 require(re.fullmatch('[0-9a-f]{32}',identifier) is not None,'fresh32hex source ID')
 out=sources();reserve='arch/arm64/mm/note10_xnu_reserve.c'
 body=out[reserve];require(digest(body)=='9da5f31aab5fe6ea0072e8c20ace8a19bbd54248d64d0808e87b3f098d869a4e','exact baseline body')
 anchor=b'static int __init note10_check_xnu_window(void)'
 require(body.count(anchor)==1,'unique full caller');body=body.replace(anchor,INCLUDE+b'\n'+anchor)
 epoch=b'    if (n10_arm_auto_return())'
 require(body.count(epoch)==1,'unique auto-return admission')
 body=body.replace(epoch,b'#ifdef CONFIG_NOTE10_PRE_PM_TRIAL\n    unsigned long n10_pre_pm_epoch = jiffies;\n#endif\n\n'+epoch)
 hook=b'    n10_start_pm_timer();'
 require(body.count(hook)==1,'unique PM queue call')
 body=body.replace(hook,b'#ifdef CONFIG_NOTE10_PRE_PM_TRIAL\n    if (n10_pre_pm_trial(reserved,count,invalid,n10_pre_pm_epoch))\n        return 0;\n#endif\n'+hook)
 out[reserve]=b'#define N10_RESERVE_BUILD_ID "'+identifier.encode()+b'"\n'+body
 out['arch/arm64/Kconfig']+=KCONFIG
 for name in NEW:out['arch/arm64/mm/'+name]=(ROOT/'note10/device_test'/name).read_bytes()
 out['arch/arm64/mm/kernel_trial_stack_oracle.c']=(ROOT/'note10/device_test/kernel_trial_stack_oracle.c').read_bytes()
 for name in TRIAL:out['arch/arm64/mm/'+name]=(ROOT/'note10/xnu26'/name).read_bytes()
 return out
def install(source,identifier):
 rows=render(identifier)
 for name,raw in rows.items():
  dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 return {name:digest(raw) for name,raw in rows.items()}
def config_settings(enabled):
 d=json.loads((BASE/'config.json').read_text())['settings'];d[OPTION]='y' if enabled else 'n';return d
