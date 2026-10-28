"""Compose bounded CPU0 PM preconditions into the pinned diagnostic tree."""
import hashlib,shutil
from pathlib import Path
from prepare_pm_callbacks import HERE, replace
from prepare_pm_irq import PINS as IRQ_PINS
PINS={'drivers/perf/arm_pmu_platform.c':'a1b8f2b8fcb2bc909f5829dc583c0e9a02409fb4383765df6a912affc3fcca2b','drivers/irqchip/irq-gic.c':'b236ffb45d4269a0f1117bb5434ea2dc795ca9ec383ec164077cbf43096780eb','drivers/clocksource/arm_arch_timer.c':'4b3d7bd50f48677962b650e7eef74320d3ae7e94df9806094723aa1eaf4039e4','arch/arm64/kernel/fpsimd.c':'341383667bf95d1294dcf71fd8c698730fc8344b2bb8743fd1094a7062f61782','kernel/sched/cpufreq_schedutil.c':'fabba38eb63688877f336b73b79434804924263faffe69484fce2c7fac792d24','drivers/perf/arm_pmu.c':'e844c142e8b89d636a01bfafdd613fd7c404a39d0ccba2ee59cbcd35a35c2ed2','drivers/soc/samsung/debug/exynos-ehld.c':'d305f58ea29e26cb9ea823a2c14ff3d544a8e90b95a08b3b8a15ebba40406605','include/linux/perf/arm_pmu.h':'a47bd6a0390265e20071362adb21f7132d8a922f1c86b5713c22959bd47c6457','include/linux/timer.h':'45f53109a46adb927c5997c262f41ae13100a5cd80011dd2e8949ef1eccc057f','include/linux/irqchip/arm-gic.h':'191b5bd2eda66923b503f8c56186eb9001358941341207b5d5dceaf0fad4fbc6'}
FILES={'include/linux/note10_pm_preconditions.h':'pm_preconditions_contract.h','drivers/irqchip/note10_pm_pre_gic_getter.c':'pm_preconditions_gic_getter.c','drivers/clocksource/note10_pm_pre_timer_getter.c':'pm_preconditions_timer_getter.c','arch/arm64/kernel/note10_pm_pre_fpsimd_getter.c':'pm_preconditions_fpsimd_getter.c','kernel/sched/note10_pm_pre_sugov_getter.c':'pm_preconditions_sugov_getter.c','drivers/perf/note10_pm_pre_pmu_getter.c':'pm_preconditions_pmu_getter.c','drivers/soc/samsung/debug/note10_pm_pre_ehld_getter.c':'pm_preconditions_ehld_getter.c','kernel/note10_pm_pre_chain.c':'pm_preconditions_chain.c','kernel/power/note10_pm_pre_capture.c':'pm_preconditions_capture.c','drivers/irqchip/note10_pm_pre_gic_regs.c':'pm_preconditions_gic_regs.c','arch/arm64/mm/note10_pm_pre_probe.c':'pm_preconditions_probe.c'}
GETTERS={'drivers/irqchip/irq-gic.c':('note10_pm_pre_gic_getter.c','note10_pm_pre_gic_regs.c'),'drivers/clocksource/arm_arch_timer.c':('note10_pm_pre_timer_getter.c',),'arch/arm64/kernel/fpsimd.c':('note10_pm_pre_fpsimd_getter.c',),'kernel/sched/cpufreq_schedutil.c':('note10_pm_pre_sugov_getter.c',),'drivers/perf/arm_pmu.c':('note10_pm_pre_pmu_getter.c',),'drivers/soc/samsung/debug/exynos-ehld.c':('note10_pm_pre_ehld_getter.c',),'kernel/cpu_pm.c':('note10_pm_pre_chain.c',)}
KCONFIG=b'\nconfig NOTE10_CPU_PM_PRECONDITIONS\n\tbool "Experimental CPU0 PM preconditions"\n\tdepends on NOTE10_CPU_PM_FAILURE_GUARD && NOTE10_PM_IRQ_TEST && NOTE10_PM_CALLBACK_INVENTORY && CPU_FREQ_GOV_SCHEDUTIL=y && ARM_ARCH_TIMER && ARM_PMU && EXYNOS_EHLD && ARM_GIC && ARM64\n\tdefault n\n'
def sha(b):return hashlib.sha256(b).hexdigest()
def includes(names):return b''.join(b'\n#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n#include "'+n.encode()+b'"\n#endif\n' for n in names)
def prepare(source,prior):
 source=Path(source)
 for n,h in PINS.items():
  if n=='drivers/irqchip/irq-gic.c':
   raw=(source/n).read_bytes()
   if sha(raw)!=prior['pm_irq_prepared_sha256'][n]:raise ValueError('prior GIC composition differs')
   for suffix in (b'\n#ifdef CONFIG_NOTE10_PM_IRQ_TEST\n#include "note10_pm_irq_gic.c"\n#endif\n',b'\n#ifdef CONFIG_NOTE10_GIC_ROUNDTRIP\n#include "note10_gic_roundtrip.c"\n#endif\n'):
    if not raw.endswith(suffix):raise ValueError('prior GIC layer differs')
    raw=raw[:-len(suffix)]
   if sha(raw)!=h:raise ValueError('original GIC pin differs')
  elif sha((source/n).read_bytes())!=h:raise ValueError('precondition pin differs: '+n)
 if sha((source/'kernel/power/note10_pm_irq.c').read_bytes())!=prior['pm_irq_prepared_sha256']['kernel/power/note10_pm_irq.c']:raise ValueError('precondition prior IRQ helper differs')
 for n in ('kernel/cpu_pm.c','kernel/power/note10_pm_noirq.c','kernel/power/note10_pm_cpus.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','kernel/power/Kconfig'):
  if sha((source/n).read_bytes())!=prior['pm_callbacks_prepared_sha256'][n]:raise ValueError('precondition prior callback source differs: '+n)
 changed=set(PINS)|set(GETTERS)|{'kernel/power/note10_pm_noirq.c','kernel/power/note10_pm_cpus.c','kernel/power/note10_pm_irq.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','kernel/power/Kconfig'}
 intermediate={n:sha((source/n).read_bytes()) for n in changed}
 for target,name in FILES.items():
  dst=source/target
  if dst.exists():raise ValueError('precondition target exists')
  dst.write_bytes((HERE/name).read_bytes())
 for target,names in GETTERS.items():
  f=source/target;f.write_bytes(f.read_bytes()+includes(names))
 cpu=source/'kernel/power/note10_pm_cpus.c';raw=cpu.read_bytes();anchor=b'#ifdef CONFIG_NOTE10_PM_IRQ_TEST\n#include "note10_pm_irq.c"\n#endif'
 raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n#include "note10_pm_pre_capture.c"\n#endif\n'+anchor)
 anchor=b'    /* Mandatory even when freeze_secondary_cpus failed part-way. */'
 raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n    if (!result) result=n10_pre_capture(generation);\n#endif\n'+anchor);cpu.write_bytes(raw)
 irq=source/'kernel/power/note10_pm_irq.c';raw=irq.read_bytes()
 for phase in range(3):
  old=('    if (!error) { error=n10_irq_gic_capture('+str(phase)+',&s->gic['+str(phase)+']);n10_pm_irq_error(s,error); }').encode()
  extra=('\n#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n    if (!error) { error=n10_pre_gic_step(generation,'+str(phase)+',s->gic['+str(phase)+'].cpu_ctlr,s->gic['+str(phase)+'].pmr);n10_pm_irq_error(s,error); }\n#endif').encode()
  raw=replace(raw,old,old+extra)
 irq.write_bytes(raw)
 worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw=worker.read_bytes();anchor=b'static bool n10_timer_done;'
 raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n#include "note10_pm_pre_probe.c"\n#endif')
 anchor=b'    int result, error = 0, i;';raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n    bool preconditions_reported=false;\n#endif')
 anchor=b'    status = 0;\nreport:';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n    preconditions_reported=true;\n    if (n10_report_pm_preconditions(pm.qgeneration,0)) goto report;\n#endif\n'+anchor+b'\n#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n    if (status && !preconditions_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())\n        (void)n10_report_pm_preconditions(pm.qgeneration,-EIO);\n#endif');worker.write_bytes(raw)
 config=source/'kernel/power/Kconfig';config.write_bytes(config.read_bytes()+KCONFIG)
 final={n:sha((source/n).read_bytes()) for n in changed|set(FILES)}
 return {'pm_preconditions_diagnostic':True,'pm_preconditions_version':1,'pm_preconditions_pins':PINS,'pm_preconditions_intermediate_sha256':intermediate,'pm_preconditions_prepared_sha256':final}
def snapshot(source,out,prepared):
 source=Path(source);out=Path(out)
 if out.exists():raise ValueError('precondition snapshot exists')
 for name,digest in prepared.items():
  rel=Path(name);src=source/rel
  if rel.is_absolute() or '..' in rel.parts or src.is_symlink() or sha(src.read_bytes())!=digest:raise ValueError('precondition snapshot differs')
  dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
