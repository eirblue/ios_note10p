"""Prepare bounded CPU0 local-IRQ observations inside the existing noirq stop."""
import hashlib
from pathlib import Path
from prepare_dma_pm import HERE
from prepare_gic_roundtrip import PIN as GIC_PIN
from prepare_pm_noirq import FINAL_SHA
PINS={
 'drivers/irqchip/irq-gic.c':GIC_PIN,
 'arch/arm64/include/asm/irqflags.h':'a716993cce81b3f54094e863e15338b5a3cff17288981d49b3b5dd72509ac917',
 'include/linux/irqflags.h':'34b7803ceab427776a308838b22e6531b406b38e882e6f03754a1d3062288481',
 'include/linux/preempt.h':'386da1a2be5458d2a6e172286987ce9fe6e8383d50377ad42a220c7026c228af',
 'arch/arm64/include/asm/Kbuild':'7c57cf62e62210fa2084e7d38a6909f931475e9732692892b237a46398520ee8',
 'include/asm-generic/preempt.h':'7d7db96b2574f7a5765722965e963b1c2907c374c72a70ad63f3e68dfc2214dd',
 'include/linux/hardirq.h':'e1d1841694fed15f3ee73707ec143ce9ac2133ee700896f7eb9e54ffb7f585b5',
 'arch/arm64/include/asm/ptrace.h':'ea9f0a6d64b675b3117c5846c29441440cdd2b3c7fe8f1e7192f64d9bdab12df',
 'include/linux/irqchip/arm-gic.h':'191b5bd2eda66923b503f8c56186eb9001358941341207b5d5dceaf0fad4fbc6',
 'arch/arm64/include/asm/io.h':'4832586f899e7c2022f5361bee4df481d24034d0448056317fb524634819ecbb',
 'include/linux/io.h':'40055099d06f1469f467fe470e2b7d30ca35a5125f480a6aa5426ef7e5b211a8',
 'include/asm-generic/io.h':'984678b0aef31acb56f2e266ed3112abda414920f2885992e9baf003cbc71ba6',
 'include/linux/debug-snapshot.h':'d1a90abd89d365b320a0210ae339bd1cee07d0ba7cb5f965192bce97707b329c',
 'arch/arm64/include/asm/sysreg.h':'a7ad04565411f8d00d3648d9a45dd862373ed8055c7133a4ab15b1124c7f8a36',
 'arch/arm64/include/asm/barrier.h':'1916bd7657459d59adbf4cadd08a605baf5ec256374eefb6d567644cf325983f',
}
SOURCES=('pm_irq_contract.h','pm_irq_backend.c','pm_irq_gic_backend.c','pm_irq_probe.c','prepare_pm_irq.py','decode_pm_irq.py','pm_irq_binding.py','test_pm_irq_native.py','test_pm_irq_decoder.py','test_pm_irq_integration_native.py','test_pm_irq_binding.py')

def replace(raw,old,new):
    if raw.count(old)!=1:raise ValueError('PM IRQ prepared insertion differs')
    return raw.replace(old,new)

def instrument_cpu(raw):
    if raw!=(HERE/'pm_cpus_backend.c').read_bytes():raise ValueError('Prepared CPU helper differs')
    include=b'#include <linux/note10_pm_cpus.h>\n'
    raw=replace(raw,include,include+b'#ifdef CONFIG_NOTE10_PM_IRQ_TEST\n#include "note10_pm_irq.c"\n#endif\n')
    old=b'    /* Mandatory even when freeze_secondary_cpus failed part-way. */'
    return replace(raw,old,b'#ifdef CONFIG_NOTE10_PM_IRQ_TEST\n    if (!result) result = n10_pm_irq_capture(generation);\n#endif\n'+old)

def prepare(source):
    source=Path(source)
    for name,digest in PINS.items():
        if name=='drivers/irqchip/irq-gic.c':continue
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('PM IRQ pinned source differs: '+name)
    suspend=source/'kernel/power/suspend.c'
    if hashlib.sha256(suspend.read_bytes()).hexdigest()!=FINAL_SHA:raise ValueError('Guarded suspend differs')
    gic=source/'drivers/irqchip/irq-gic.c';raw=gic.read_bytes();suffix=b'\n#ifdef CONFIG_NOTE10_GIC_ROUNDTRIP\n#include "note10_gic_roundtrip.c"\n#endif\n'
    if not raw.endswith(suffix) or hashlib.sha256(raw[:-len(suffix)]).hexdigest()!=GIC_PIN:raise ValueError('Pinned prepared GIC differs')
    cpu=source/'kernel/power/note10_pm_cpus.c';cpu_raw=instrument_cpu(cpu.read_bytes())
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';work=worker.read_bytes()
    if work.count(b'    if (n10_test_gic()) goto report;')!=1:raise ValueError('GIC error gate missing')
    anchor=b'static bool n10_timer_done;';work=replace(work,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_PM_IRQ_TEST\n#include "note10_pm_irq_probe.c"\n#endif')
    work=replace(work,b'    status = 0;\nreport:',b'#ifdef CONFIG_NOTE10_PM_IRQ_TEST\n    if (n10_report_pm_irq(pm.qgeneration)) goto report;\n#endif\n    status = 0;\nreport:\n#ifdef CONFIG_NOTE10_PM_IRQ_TEST\n    if (status && error && pm.qgeneration && after == 255 && num_online_cpus() == 8 && !irqs_disabled())\n        n10_report_pm_irq_failure(pm.qgeneration);\n#endif')
    paths={'include/linux/note10_pm_irq.h':'pm_irq_contract.h','kernel/power/note10_pm_irq.c':'pm_irq_backend.c',
           'drivers/irqchip/note10_pm_irq_gic.c':'pm_irq_gic_backend.c','arch/arm64/mm/note10_pm_irq_probe.c':'pm_irq_probe.c'}
    for target,name in paths.items():
        if (source/target).exists():raise ValueError('PM IRQ already prepared')
        (source/target).write_bytes((HERE/name).read_bytes())
    cpu.write_bytes(cpu_raw);worker.write_bytes(work)
    gic.write_bytes(raw+b'\n#ifdef CONFIG_NOTE10_PM_IRQ_TEST\n#include "note10_pm_irq_gic.c"\n#endif\n')
    config=source/'kernel/power/Kconfig';config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_PM_IRQ_TEST\n\tbool "Experimental CPU0 local IRQ read-only observation"\n\tdepends on NOTE10_PM_CPUS_TEST && NOTE10_PM_POST_ARCH && NOTE10_PM_EDGE_INVENTORY && NOTE10_GIC_ROUNDTRIP && ARM_GIC=y && ARM64_4K_PAGES && PREEMPT_COUNT && !GIC_NON_BANKED && !TRACE_IRQFLAGS && !DEBUG_SNAPSHOT_IRQ_DISABLED && !DEBUG_SNAPSHOT_REG\n\tdefault n\n')
    if hashlib.sha256(suspend.read_bytes()).hexdigest()!=FINAL_SHA:raise ValueError('Guarded suspend changed')
    prepared=(cpu,worker,gic,suspend,config,*(source/p for p in paths))
    return {'pm_irq_diagnostic':True,'pm_irq_evidence_version':1,'pm_irq_source_pins':PINS,
            'pm_irq_sources_sha256':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in SOURCES},
            'pm_irq_prepared_sha256':{str(p.relative_to(source)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in prepared}}
