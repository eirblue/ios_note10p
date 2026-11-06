"""Exact DSIM mapping-proxy terminal provider over immutable139 aggregate."""
from pathlib import Path
import v139_prepare as retained
HERE=Path(__file__).resolve().parent
PINS=retained.PINS
OPTION=retained.OPTION
profile=retained.profile
sha=retained.sha
BASE='drivers/video/fbdev/exynos/dpu20/'
NATIVE_PATH=BASE+'v140_dsim.inc'
CAL_PATH='drivers/soc/samsung/cal-if/v136_cal.inc'
once=retained.retained.once


def render(stock,identity,source128):
    output=retained.render(stock,identity,source128)
    header=output['include/linux/v138_display.h']
    header=once(header,b'#define N138_DPU_DOMAIN_OFF_FROZEN 7U',b'#define N138_DPU_DOMAIN_OFF_FROZEN 7U\n#define N140_DSIM_PROXY_NATIVE_FROZEN 8U\n#define N140_DSIM_PROXY_OFF_FROZEN 9U\nbool n140_native_dsim_link(void *,void *);\nint n140_dsim_final(void);')
    output['include/linux/v138_display.h']=header
    output[BASE+'decon_core.c']+=b'\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#define N140_DECON_NATIVE\n#include "v140_dsim.inc"\n#endif\n'
    output[BASE+'v138_display.c']+=b'\n#define N140_DSIM_CATALOG\n#include "v140_dsim.inc"\n'
    output[NATIVE_PATH]=(HERE/'v140_dsim.inc').read_bytes()
    path=CAL_PATH
    output[path]=once(output[path],b'(type==N138_DPU_DOMAIN_OFF_FROZEN && domains==N138_DPU_DOMAINS)))',b'(type==N138_DPU_DOMAIN_OFF_FROZEN && domains==N138_DPU_DOMAINS) ||\n         (type==N140_DSIM_PROXY_NATIVE_FROZEN && domains==N138_DPU_DOMAINS) ||\n         (type==N140_DSIM_PROXY_OFF_FROZEN && domains==N138_DPU_DOMAINS)))')
    path='arch/arm64/mm/v130_kernel.c'
    output[path]=once(output[path],b'    if(!result)result=n138_display_final();',b'    if(!result)result=n138_display_final();\n    if(!result)result=n140_dsim_final();')
    output['include/linux/v130_kernel_api.h']=once(output['include/linux/v130_kernel_api.h'],b'int n138_display_final(void);',b'int n138_display_final(void);\nint n140_dsim_final(void);')
    return {name:raw.replace(b'N10XNU139',b'N10XNU140') for name,raw in output.items()}


def install(source,identity,source128):
    source=Path(source).resolve();stock={name:(source/name).read_bytes() for name in PINS}
    output=render(stock,identity,source128)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('unsafe140 native overlay path')
        if name not in PINS and path.exists():raise ValueError('new140 component exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:sha(raw) for name,raw in output.items()}
