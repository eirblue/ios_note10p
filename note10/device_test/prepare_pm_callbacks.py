"""Compose callback inventory into pinned kernel translation units (v35)."""
import hashlib
import shutil
from pathlib import Path
from prepare_pm_noirq import FINAL_SHA
from prepare_pm_irq import instrument_cpu
from prepare_dma_pm import HERE
PINS = {
 'kernel/cpu_pm.c':'25cf098329a8f3d5487b6779726796b42081935a2bba4bb4a596d1e95f48fee1',
 'kernel/notifier.c':'ab19243be9cf32c9943fcdc352fef42357274ed4bbc9043f770f62e77bc968c5',
 'kernel/irq/generic-chip.c':'6c83ea18ef12d6590efb1bd699e96e690d95b934543b27f1f89742d202d9d545',
 'kernel/time/clocksource.c':'a56b96cd62bcd7f00800f76574f6edbdfadd8d8cda64d88c61dcc707a127f8c9',
 'kernel/time/clockevents.c':'2c62669cb18b13176b339dca314e2e8216da7261d27854e79a336e27338175b8',
 'include/linux/clockchips.h':'327b999c4c783a3b1cc113f74957d82839bc21e762ae84a2371dacdede965138',
 'kernel/locking/mutex.c':'e0f281e80e2c2ae72938b9001c93429de1bc3b9518a035350515c7ac579d3fe6',
 'include/linux/mutex.h':'547717f6b223664ce794e9fcf936fa75d01bbec7aea909e8b46e8b0d00358aa4',
 'include/linux/spinlock_api_smp.h':'e38b2efdb2b84888f2e204f524a30ccf4021e6561067c23c20da586511ab97f6',
 'include/linux/spinlock.h':'ea3a2447a9c005f9f05e20a12bfd5b0555f7298c3b386261fb980afe66b27d00',
 'arch/arm64/include/asm/spinlock.h':'aac67319de0ae323dc7ab912aaaba8547a603729931ce3c328ad789877e2aad8',
 'kernel/locking/spinlock.c':'d4ce3d228f6fccdfd241dfe4ed23986c2ef94ffd9111341f25fb20502748214c',
}
SOURCES=('pm_callbacks_contract.h','pm_callbacks_backend.c','pm_callbacks_cpu_pm_backend.c','pm_callbacks_irq_backend.c','pm_callbacks_clocksource_backend.c','pm_callbacks_clockevent_backend.c','pm_callbacks_probe.c','prepare_pm_callbacks.py','decode_pm_callbacks.py','pm_callbacks_binding.py','test_pm_callbacks_dispatcher_native.py','test_pm_callbacks_families_native.py','test_pm_callbacks_producer.py','test_pm_callbacks_integration_native.py','test_pm_callbacks_lock_native.py','test_pm_callbacks_decoder.py','test_pm_callbacks_binding.py','test_pm_callbacks_prepared_binding.py','test_pm_callbacks_full_binding.py')
FILES={'include/linux/note10_pm_callbacks.h':'pm_callbacks_contract.h','kernel/power/note10_pm_callbacks.c':'pm_callbacks_backend.c','kernel/note10_pm_callbacks_cpu_pm.c':'pm_callbacks_cpu_pm_backend.c','kernel/irq/note10_pm_callbacks_irq.c':'pm_callbacks_irq_backend.c','kernel/time/note10_pm_callbacks_clocksource.c':'pm_callbacks_clocksource_backend.c','kernel/time/note10_pm_callbacks_clockevent.c':'pm_callbacks_clockevent_backend.c','arch/arm64/mm/note10_pm_callbacks_probe.c':'pm_callbacks_probe.c'}
def replace(raw, old, new):
    if raw.count(old)!=1: raise ValueError('Callback composition anchor differs')
    return raw.replace(old,new)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def prepare(source):
    source=Path(source)
    for name,digest in PINS.items():
        if sha((source/name).read_bytes()) != digest: raise ValueError('Callback pinned source differs: '+name)
    suspend=source/'kernel/power/suspend.c'
    if sha(suspend.read_bytes())!=FINAL_SHA: raise ValueError('Guarded suspend differs')
    cpu=source/'kernel/power/note10_pm_cpus.c'; raw=cpu.read_bytes()
    if raw != instrument_cpu((HERE/'pm_cpus_backend.c').read_bytes()): raise ValueError('IRQ prepared CPU caller differs')
    noirq=source/'kernel/power/note10_pm_noirq.c'; noirq_raw=noirq.read_bytes()
    dma=source/'drivers/base/power/note10_dma_pm.c'; dma_raw=dma.read_bytes()
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c'; work=worker.read_bytes()
    intermediate={str(p.relative_to(source)).replace('\\','/'):sha(p.read_bytes()) for p in (cpu,noirq,dma,worker,suspend,source/'kernel/power/Kconfig')}
    raw=replace(raw,b'    /* Mandatory even when freeze_secondary_cpus failed part-way. */',b'#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n    if (!result) result = n10_cb_capture(1, generation);\n#endif\n    /* Mandatory even when freeze_secondary_cpus failed part-way. */')
    raw=replace(raw,b'    if (s->restored != s->before || num_online_cpus() != 8 || irqs_disabled()) result = -EIO;',b'#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n    if (s->restored != s->before || num_online_cpus() != 8 || irqs_disabled()) { if (!result) result = -EIO; }\n#else\n    if (s->restored != s->before || num_online_cpus() != 8 || irqs_disabled()) result = -EIO;\n#endif')
    raw=b'#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n#include <linux/note10_pm_callbacks.h>\n#endif\n'+raw
    noirq_raw+=b'\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n#include "note10_pm_callbacks.c"\n#endif\n'
    marker=b'    if (phase == 0 || phase == 2) n10_edge_capture(phase == 0 ? 0 : 3, generation);'
    dma_raw=replace(dma_raw,marker,marker+b'\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n    if (phase == 0 || phase == 2) (void)n10_cb_capture(phase == 0 ? 0 : 2, generation);\n#endif')
    dma_raw=b'#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n#include <linux/note10_pm_callbacks.h>\n#endif\n'+dma_raw
    anchor=b'static bool n10_timer_done;'
    work=replace(work,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n#include "note10_pm_callbacks_probe.c"\n#endif')
    work=replace(work,b'    int result, error = 0, i;',b'    int result, error = 0, i;\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n    bool callbacks_reported = false;\n#endif')
    work=replace(work,b'    status = 0;\nreport:',b'#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n    callbacks_reported = true;\n    if (n10_report_pm_callbacks(pm.qgeneration, 0)) goto report;\n#endif\n    status = 0;\nreport:\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n    if (status && !callbacks_reported && pm.qgeneration && after == 255 && num_online_cpus() == 8 && !irqs_disabled())\n        (void)n10_report_pm_callbacks(pm.qgeneration, -EIO);\n#endif')
    for target,name in FILES.items():
        p=source/target
        if p.exists(): raise ValueError('Callback helper already exists')
        p.write_bytes((HERE/name).read_bytes())
    for target,helper in (('kernel/cpu_pm.c','note10_pm_callbacks_cpu_pm.c'),('kernel/irq/generic-chip.c','note10_pm_callbacks_irq.c'),('kernel/time/clocksource.c','note10_pm_callbacks_clocksource.c'),('kernel/time/clockevents.c','note10_pm_callbacks_clockevent.c')):
        p=source/target;p.write_bytes(p.read_bytes()+('\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n#include "'+helper+'"\n#endif\n').encode())
    cpu.write_bytes(raw); noirq.write_bytes(noirq_raw); dma.write_bytes(dma_raw); worker.write_bytes(work)
    config=source/'kernel/power/Kconfig'; config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_PM_CALLBACK_INVENTORY\n\tbool "Experimental PM callback metadata inventory"\n\tdepends on NOTE10_PM_IRQ_TEST && CPU_PM && GENERIC_IRQ_CHIP && GENERIC_CLOCKEVENTS && SMP && PREEMPT_COUNT && KALLSYMS && !DEBUG_SNAPSHOT_SPINLOCK && !DEBUG_SPINLOCK && !DEBUG_MUTEXES && !DEBUG_LOCK_ALLOC\n\tdefault n\n')
    if sha(suspend.read_bytes())!=FINAL_SHA: raise ValueError('Guarded suspend changed')
    paths=[cpu,noirq,dma,worker,suspend,config]+[source/p for p in FILES]+[source/p for p in ('kernel/cpu_pm.c','kernel/irq/generic-chip.c','kernel/time/clocksource.c','kernel/time/clockevents.c')]
    return {'pm_callbacks_diagnostic':True,'pm_callbacks_evidence_version':1,'pm_callbacks_source_pins':PINS,'pm_callbacks_sources_sha256':{n:sha((HERE/n).read_bytes()) for n in SOURCES},'pm_callbacks_intermediate_sha256':intermediate,'pm_callbacks_prepared_sha256':{str(p.relative_to(source)).replace('\\','/'):sha(p.read_bytes()) for p in paths}}

def snapshot_prepared(source, output, prepared):
    source=Path(source);output=Path(output)
    if output.exists():raise ValueError('Callback prepared snapshot already exists')
    for name,digest in prepared.items():
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe prepared snapshot path')
        src=source/rel
        if src.is_symlink() or not src.is_file() or sha(src.read_bytes())!=digest:raise ValueError('Prepared snapshot source differs: '+name)
        dst=output/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    return output
