"""Opt-in source integration, pinned Samsung reboot route inspection."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
PINS={
 'kernel/reboot.c':'ed27858a87e0b7fe098510f03054c034a333874017444de2052af3e691d5b3f8',
 'drivers/samsung/sec_reboot.c':'9c598d65fac6c7be4ba9bcf1d3f6d7d5ec218844c28b97653deabc707190d594',
 'drivers/soc/samsung/exynos-reboot.c':'be332988d59a77ae616a86bd70ac52ecae6dff94715239b84450a22c02633cf8'}

def prepare(source,path,extension):
    for name,digest in PINS.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Pinned restart implementation differs: '+name)
    actual=(HERE/'auto_return.c').read_bytes()
    target=path.with_name('note10_auto_return.c')
    if target.exists():raise ValueError('Existing auto-return extension')
    include=b'#include "note10_pm_timer_roundtrip.c"\n'
    if extension.count(include)!=1:raise ValueError('PM worker prerequisite missing')
    extension=extension.replace(include,b'#include "note10_auto_return.c"\n'+include)
    local=b'    unsigned long start, count, i, reserved = 0, invalid = 0;\n'
    if extension.count(local)!=1:raise ValueError('Unexpected reservation gate')
    extension=extension.replace(local,local+b'\n    if (n10_arm_auto_return())\n        return 0;\n')
    target.write_bytes(actual)
    return extension,dict(auto_return_diagnostic=True,auto_return_evidence_version=1,
        auto_cycle_slot="N10_CYCLE_SLOT_UNSET_0123456789A",auto_return_delay_ms=90000,auto_return_source_sha256=hashlib.sha256(actual).hexdigest(),
        auto_return_restart_source_pins=PINS,auto_return_hardware_verified=False)
