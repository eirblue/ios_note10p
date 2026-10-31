"""Default-off source-only extension of the pinned reservation-only init.c TU."""
from pathlib import Path
import prepare_xnu_runtime_plan as canonical
from relocation_trial_aarch64_model import ROOT,require,sha

OPTION='CONFIG_NOTE10_KERNEL_TRIAL_COMPONENT'
ENTRY='n10_kernel_trial_adapter'
FILES=('runtime_relocation.c','runtime_relocation.h','runtime_relocation_trial.c','runtime_relocation_trial.h')
EXTRAS=('relocation_trial_aarch64_abi.c','kernel_trial_adapter.c','kernel_trial_stack_oracle.c')
BLOCK=b'\nconfig NOTE10_KERNEL_TRIAL_COMPONENT\n\tbool "Uninvoked PC-only kernel trial component"\n\tdepends on ARM64\n\tdefault n\n'
INCLUDE=b'''#ifdef CONFIG_NOTE10_KERNEL_TRIAL_COMPONENT
/* Isolate only component literal data; function sections remain individually collectible. */
#pragma clang section rodata=".rodata.n10_component"
#include "runtime_relocation.c"
#include "runtime_relocation_trial.c"
#include "relocation_trial_aarch64_abi.c"
#include "kernel_trial_adapter.c"
#include "kernel_trial_stack_oracle.c"
#pragma clang section rodata=""
#endif

'''

def render(init,kconfig,enabled=False):
    require(type(enabled) is bool,'explicit boolean source opt-in')
    require(OPTION.encode() not in init+kconfig and ENTRY.encode() not in init,'duplicate component insertion')
    if not enabled:return init,kconfig
    require(init.count(canonical.CANON_INCLUDE)==1,'exact canonical insertion anchor')
    return init.replace(canonical.CANON_INCLUDE,INCLUDE+canonical.CANON_INCLUDE,1),kconfig+BLOCK

def prepare(source,baseline,enabled=False):
    source=Path(source);canonical.validate_canonical(source,baseline)
    init=source/canonical.INIT;config=source/canonical.KCONFIG
    before={canonical.INIT:sha(init),canonical.KCONFIG:sha(config),canonical.RESERVE:sha(source/canonical.RESERVE)}
    new_init,new_config=render(init.read_bytes(),config.read_bytes(),enabled)
    copied={}
    if enabled:
        for name in FILES+EXTRAS:
            original=ROOT/('note10/xnu26/' if name in FILES else 'note10/device_test/')/name
            target=init.parent/name;require(not target.exists(),'component output exists')
            target.write_bytes(original.read_bytes());copied[name]=sha(target)
        init.write_bytes(new_init);config.write_bytes(new_config)
    return {'schema':1,'enabled':enabled,'before_sha256':before,
      'after_sha256':{name:sha(source/name) for name in before},'copied_sha256':copied,
      'default_off':True,'adapter_invoked_from_boot':False,'literal_section_instrumentation':'.rodata.n10_component pragma only; no text grouping',
      'deployment_ready':False,'full_image_built':False,'device_operations':[]}
