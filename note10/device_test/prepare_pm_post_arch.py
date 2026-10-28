"""Prepare read-only post-PM per-CPU state and payload observations."""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    'arch/arm64/include/asm/mmu_context.h': 'd92388a5da5e5e6f0476f7c74dbf5fef6920aef13f5a6f450a39277cb19e8567',
    'arch/arm64/mm/proc.S': 'd1d44da91b25a036ddd0fcc4b8c1b78a34d0f9ff631295d3b70387edb035feb3',
    'arch/arm64/include/asm/assembler.h': '241d6cadfaf2034c5efc5458b6f136c3fc19fac30e58d8e544bcf74d8a48082b',
    'arch/arm64/mm/context.c': '79ee5e15e6d647965809ca5f31f4404ffb0b3ab62a8cf4377741256908466755',
}
SOURCES = ('pm_post_arch_probe.c','prepare_pm_post_arch.py','decode_pm_post_arch.py',
           'pm_post_arch_binding.py','test_pm_post_arch_native.py','test_pm_post_arch_contract.py')


def prepare(source):
    source = Path(source)
    for name, digest in PINS.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Post-PM architecture source differs: ' + name)
    worker = source / 'arch/arm64/mm/note10_pm_timer_roundtrip.c'
    raw = worker.read_bytes()
    anchor = b'static bool n10_timer_done;'
    tail = b'    status = 0;\nreport:'
    if (raw.count(anchor) != 1 or raw.count(tail) != 1 or
        raw.count(b'    n10_test_gic();') != 1 or
        raw.count(b'    n10_report_pm_cpus(pm.qgeneration);') != 1 or
        raw.count(b'n10_report_pm_cpu_timers(pm.qgeneration)') != 1):
        raise ValueError('Post-PM prerequisites or insertion point differ')
    helper = worker.with_name('note10_pm_post_arch_probe.c')
    if helper.exists():
        raise ValueError('Post-PM observer already prepared')
    helper.write_bytes((HERE / 'pm_post_arch_probe.c').read_bytes())
    raw = raw.replace(anchor, anchor + b'\n#ifdef CONFIG_NOTE10_PM_POST_ARCH\n#include "note10_pm_post_arch_probe.c"\n#endif')
    code = (b'#ifdef CONFIG_NOTE10_PM_POST_ARCH\n'
            b'    if (n10_report_post_arch(memory, pm.qgeneration)) goto report;\n'
            b'    result = n10_sha256(memory, length, digest);\n'
            b'    if (result || memcmp(digest, expected, sizeof(expected))) goto report;\n'
            b'#endif\n')
    worker.write_bytes(raw.replace(tail, code + tail))
    config = source / 'kernel/power/Kconfig'
    data = config.read_bytes()
    if b'config NOTE10_PM_POST_ARCH' in data:
        raise ValueError('Existing post-PM architecture Kconfig')
    config.write_bytes(data + b'\nconfig NOTE10_PM_POST_ARCH\n\tbool "Experimental read-only post-PM CPU observations"\n\tdepends on NOTE10_PM_CPUS_TEST && NOTE10_GIC_ROUNDTRIP && ARM64_4K_PAGES\n\tdefault n\n')
    return dict(pm_post_arch_diagnostic=True, pm_post_arch_evidence_version=1,
                pm_post_arch_source_pins=PINS,
                pm_post_arch_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
                pm_post_arch_worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest())
