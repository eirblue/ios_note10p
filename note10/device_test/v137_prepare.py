"""Surgical CAL kernel-macro repair over immutable136 native terminal proof."""
from pathlib import Path
import re
import v136_prepare as retained
HERE=Path(__file__).resolve().parent
PINS=retained.PINS
OPTION=retained.OPTION
profile=retained.profile
sha=retained.sha
CAL_PATH='drivers/soc/samsung/cal-if/v136_cal.inc'
CAL_SHA='200b47ab35e7f5430e427955046e0db6e15403edd5b4ba35225efe0bde62c740'


def cal_source(raw):
    if sha(raw)!=CAL_SHA or len(re.findall(rb'\bcurrent\b',raw))!=7:raise ValueError('exact immutable136 CAL macro collision scope required')
    return re.sub(rb'\bcurrent\b',b'n137_snapshot_state',raw).replace(b'N10XNU136',b'N10XNU137')


def render(stock,identity,source128):
    output=retained.render(stock,identity,source128)
    output[CAL_PATH]=cal_source(output[CAL_PATH])
    return {name:raw.replace(b'N10XNU136',b'N10XNU137') for name,raw in output.items()}


def install(source,identity,source128):
    source=Path(source).resolve();stock={name:(source/name).read_bytes() for name in PINS};output=render(stock,identity,source128)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('unsafe137 native overlay path')
        if name not in PINS and path.exists():raise ValueError('new137 component exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:sha(raw) for name,raw in output.items()}
