"""Bundle paired original CPU hotplug and a separate CPU-stop PMU snapshot."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
PINS={'kernel/cpu.c':'9d6e1b1c5e1937fbd99c26923310953825cb7f58255aca7a830e32079476738c',
      'include/linux/cpu.h':'cfd98e81e72d50a9291414ec3bce5def163a7fa53971a4d885762aaf0a3c7936'}
SOURCES=('pm_cpus_contract.h','pm_cpus_backend.c','pm_cpus_pmu.c','pm_cpus_probe.c','pm_cpus_timer_probe.c','pm_cpus_workqueue.c','prepare_pm_cpus.py','decode_pm_cpus.py','pm_cpus_binding.py','test_pm_cpu_hotplug_native.py','test_pm_cpus_pmu_native.py','test_pm_cpus_timer_native.py','test_pm_cpus_queue_native.py')

def prepare(source):
    source=Path(source)
    for name,digest in PINS.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('CPU hotplug source differs: '+name)
    for name,original in {'kernel/power/note10_pm_noirq.c':'pm_noirq_backend.c',
                          'sound/soc/samsung/abox/note10_abox_pmu.c':'abox_pmu_backend.c'}.items():
        if (source/name).read_bytes()!=(HERE/original).read_bytes():raise ValueError('CPU diagnostic prerequisite helper differs')
    files={'include/linux/note10_pm_cpus.h':'pm_cpus_contract.h','kernel/power/note10_pm_cpus.c':'pm_cpus_backend.c',
           'sound/soc/samsung/abox/note10_pm_cpus_pmu.c':'pm_cpus_pmu.c','arch/arm64/mm/note10_pm_cpus_probe.c':'pm_cpus_probe.c',
           'arch/arm64/mm/note10_pm_cpus_timer_probe.c':'pm_cpus_timer_probe.c',
           'arch/arm64/mm/note10_pm_cpus_workqueue.c':'pm_cpus_workqueue.c'}
    if any((source/n).exists() for n in files):raise ValueError('Existing CPU diagnostic extension')
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw=worker.read_bytes()
    anchor=b'    error = n10_pm_devices_test(&pm);'
    if raw.count(anchor)!=1:raise ValueError('CPU diagnostic report anchor differs')
    timer_anchor=b'static struct n10_timer_sample n10_timers[8];'
    after_anchor=b'    after = n10_online_bits();'
    if raw.count(timer_anchor)!=1 or raw.count(after_anchor)!=1:raise ValueError('CPU timer readback anchor differs')
    # n10_timer_done is declared later; put the include after its declaration.
    timer_anchor=b'static bool n10_timer_done;'
    if raw.count(timer_anchor)!=1:raise ValueError('CPU timer completion state differs')
    raw=raw.replace(timer_anchor,timer_anchor+b'\n#ifdef CONFIG_NOTE10_PM_CPUS_TEST\n#include "note10_pm_cpus_timer_probe.c"\n#endif')
    raw=raw.replace(after_anchor,after_anchor+b'\n#ifdef CONFIG_NOTE10_PM_CPUS_TEST\n    if (!error && n10_timer_done && after == 255) n10_report_pm_cpu_timers(pm.qgeneration);\n#endif')
    queue_anchor=b'static DECLARE_DELAYED_WORK(n10_pm_work, n10_pm_worker);'
    schedule_anchor=b'schedule_delayed_work(&n10_pm_work, '
    if raw.count(queue_anchor)!=1 or raw.count(schedule_anchor)!=3:raise ValueError('PM worker scheduler anchors differ')
    raw=raw.replace(queue_anchor,queue_anchor+b'\n#include "note10_pm_cpus_workqueue.c"')
    raw=raw.replace(schedule_anchor,b'n10_pm_cpus_schedule(')
    for name,original in files.items():(source/name).write_bytes((HERE/original).read_bytes())
    worker.write_bytes(b'#ifdef CONFIG_NOTE10_PM_CPUS_TEST\n#include "note10_pm_cpus_probe.c"\n#endif\n'+raw.replace(anchor,
        anchor+b'\n#ifdef CONFIG_NOTE10_PM_CPUS_TEST\n    n10_report_pm_cpus(pm.qgeneration);\n#endif'))
    k=source/'kernel/power/Kconfig';k.write_bytes(k.read_bytes()+b'\nconfig NOTE10_PM_CPUS_TEST\n\tbool "Experimental paired CPU hotplug at guarded noirq stop"\n\tdepends on NOTE10_PM_NOIRQ_TEST && HOTPLUG_CPU && PM_SLEEP_SMP\n\tdefault n\n')
    return dict(pm_cpus_diagnostic=True,pm_cpus_evidence_version=1,pm_cpus_source_pins=PINS,
        pm_cpus_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES})
