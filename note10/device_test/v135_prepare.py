"""Narrow EVT1 reset hardware overlay over immutable133 lifetime providers."""
from pathlib import Path
import v133_prepare as retained
HERE=Path(__file__).resolve().parent
PINS=dict(retained.PINS)
OPTION=retained.OPTION
once=retained.once
sha=retained.sha


def profile(settings):
    required={'NOTE10_XNU_KEXEC_HANDOFF':'y','SOC_EXYNOS9820':'y','SOC_EXYNOS9820_EVT0':'n',
              'EXYNOS_SCORE':'y','EXYNOS_SCORE_V3':'y','EXYNOS_SCORE_V2':'n','EXYNOS_SCORE_FPGA':'n'}
    if any(settings.get(k)!=v for k,v in required.items()):
        raise ValueError('exact native non-FPGA Exynos9820 EVT1 SCORE profile required')
    return required


def render(stock,identity,source128):
    output=retained.render(stock,identity,source128)
    original=(HERE/'v133_score.inc').read_bytes()
    start=original.index(b'int n133_score_hardware_stop(')
    end=original.index(b'\n#else\n',start)
    replacement=original[:start]+b'#include "v135_score_reset.inc"\n'+original[end:]
    replacement=once(replacement,b'stage="score-halt";',b'stage="score-reset";')
    replacement=replacement.replace(b'N10XNU133',b'N10XNU135')
    for name,raw in output.items():output[name]=raw.replace(b'N10XNU133',b'N10XNU135')
    output['drivers/vision/score/v133_score.inc']=replacement
    output['drivers/vision/score/hardware/v3/v133_score.inc']=replacement
    output['drivers/vision/score/hardware/v3/v135_score_reset.inc']=(HERE/'v135_score_reset.inc').read_bytes()
    return output


def install(source,identity,source128):
    source=Path(source).resolve();stock={name:(source/name).read_bytes() for name in PINS}
    output=render(stock,identity,source128)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('unsafe EVT1 overlay path')
        if name not in PINS and path.exists():raise ValueError('new EVT1 component already exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:sha(raw) for name,raw in output.items()}
