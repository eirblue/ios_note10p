"""Opt-in bounded CPU-interface PMR roundtrip in the pinned GICv2 driver."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
PIN='b236ffb45d4269a0f1117bb5434ea2dc795ca9ec383ec164077cbf43096780eb'
SOURCES=('gic_roundtrip_backend.c','gic_roundtrip_probe.c','gic_roundtrip_contract.h','prepare_gic_roundtrip.py','decode_gic_roundtrip.py','gic_roundtrip_binding.py')

def prepare(source):
    source=Path(source);path=source/'drivers/irqchip/irq-gic.c';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PIN:raise ValueError('Pinned GIC driver differs')
    helper=path.with_name('note10_gic_roundtrip.c')
    if helper.exists():raise ValueError('GIC diagnostic already prepared')
    helper.write_bytes((HERE/'gic_roundtrip_backend.c').read_bytes())
    (source/'include/linux/note10_gic_roundtrip.h').write_bytes((HERE/'gic_roundtrip_contract.h').read_bytes())
    path.write_bytes(raw+b'\n#ifdef CONFIG_NOTE10_GIC_ROUNDTRIP\n#include "note10_gic_roundtrip.c"\n#endif\n')
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c'
    text=worker.read_bytes();anchor=b'    status = 0;\nreport:'
    if text.count(anchor)!=1:raise ValueError('PM worker GIC insertion point differs')
    worker.with_name('note10_gic_roundtrip_probe.c').write_bytes((HERE/'gic_roundtrip_probe.c').read_bytes())
    text=b'#ifdef CONFIG_NOTE10_GIC_ROUNDTRIP\n#include "note10_gic_roundtrip_probe.c"\n#endif\n'+text.replace(anchor,b'#ifdef CONFIG_NOTE10_GIC_ROUNDTRIP\n    if (n10_test_gic()) goto report;\n    result = n10_sha256(memory, length, digest);\n    if (result || memcmp(digest, expected, sizeof(expected))) goto report;\n#endif\n'+anchor)
    worker.write_bytes(text)
    config=source/'kernel/power/Kconfig'
    if b'config NOTE10_GIC_ROUNDTRIP' in config.read_bytes():raise ValueError('Existing GIC diagnostic Kconfig')
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_GIC_ROUNDTRIP\n\tbool "Experimental reversible GICv2 CPU priority mask diagnostic"\n\tdepends on NOTE10_PM_QUIESCE && ARM_GIC=y && SMP\n\tdefault n\n')
    return dict(gic_roundtrip_diagnostic=True,gic_roundtrip_evidence_version=1,
        gic_roundtrip_source_pin=PIN,gic_roundtrip_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
        gic_roundtrip_patched_driver_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        gic_roundtrip_patched_worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
        gic_roundtrip_hardware_verified=False)
