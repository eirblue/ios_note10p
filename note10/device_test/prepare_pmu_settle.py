"""Read-only delayed PMU snapshots after a completed guarded roundtrip."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCES=('pmu_settle_contract.h','pmu_settle_backend.c','pmu_settle_gate.c','pmu_settle_probe.c','prepare_pmu_settle.py','decode_pmu_settle.py','pmu_settle_binding.py')

def prepare(source):
    source=Path(source)
    for target,original in {'kernel/power/note10_pm_noirq.c':'pm_noirq_backend.c',
                            'sound/soc/samsung/abox/note10_abox_pmu.c':'abox_pmu_backend.c',
                            'include/linux/note10_pm_noirq.h':'pm_noirq_contract.h'}.items():
        if (source/target).read_bytes()!=(HERE/original).read_bytes():raise ValueError('Timed PMU prerequisite helper differs')
    files={'sound/soc/samsung/abox/note10_pmu_settle.c':'pmu_settle_backend.c',
           'kernel/power/note10_pmu_settle_gate.c':'pmu_settle_gate.c',
           'include/linux/note10_pmu_settle.h':'pmu_settle_contract.h',
           'arch/arm64/mm/note10_pmu_settle_probe.c':'pmu_settle_probe.c'}
    if any((source/n).exists() for n in files):raise ValueError('Existing PMU settle observer')
    for name,original in files.items():(source/name).write_bytes((HERE/original).read_bytes())
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw=worker.read_bytes()
    if raw.count(b'n10_report_pm_noirq(pm.qgeneration);')!=1:raise ValueError('Guarded noirq report prerequisite missing')
    anchor=b'\n}\n\nstatic void n10_start_pm_timer(void)'
    if raw.count(anchor)!=1:raise ValueError('PM completion report anchor differs')
    raw=raw.replace(anchor,b'\n#ifdef CONFIG_NOTE10_PMU_SETTLE\n    if (!status) n10_arm_pmu_settle(pm.qgeneration);\n#endif'+anchor)
    worker.write_bytes(b'#ifdef CONFIG_NOTE10_PMU_SETTLE\n#include "note10_pmu_settle_probe.c"\n#endif\n'+raw)
    k=source/'kernel/power/Kconfig';k.write_bytes(k.read_bytes()+b'\nconfig NOTE10_PMU_SETTLE\n\tbool "Experimental delayed read-only PMU snapshots"\n\tdepends on NOTE10_PM_NOIRQ_TEST\n\tdefault n\n')
    return dict(pmu_settle_diagnostic=True,pmu_settle_evidence_version=1,
                pmu_settle_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES})
