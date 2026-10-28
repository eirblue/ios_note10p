"""Compose the scoped PMU control observer over exact v41 prepared files."""
import hashlib,shutil
from pathlib import Path
from prepare_pm_callbacks import HERE,replace
PINS={'arch/arm64/kernel/perf_event.c':'41ad76c79bcc7f6ebcc033bb445babd551f73a7704bd3ba9d5a7c9705cda38ee','arch/arm64/include/asm/perf_event.h':'19ab06a7adaaaa36cc9c479dacfc9788451f5187c3a8aa66d0e329fb41b0484b','arch/arm64/include/asm/cputype.h':'485cd2029bcf669e40503a65302a56f4c1638d8428e267572f119a147affe5bd','include/linux/perf/arm_pmu.h':'a47bd6a0390265e20071362adb21f7132d8a922f1c86b5713c22959bd47c6457','include/linux/string.h':'4cf7d8c3d9b194b821a4c832a80bc91e5f2cb6554f51561b88c2f46aacdb55fb','include/linux/compiler.h':'343708c983b5c45cdc5575a43654757969723b66b02fa1483bbc3a6a655c7765','include/linux/compiler-gcc.h':'cdd7c6ef076b771b1cf3598a8dd2de70dad38ff33bbb5f142d29d09e78c16d40','include/linux/compiler-clang.h':'8ff9164115a9c42fdf19ed9b8bde0ce3592ad82ec0c4f068e752a3cbf3c1ec5f','lib/string.c':'fc869eb46f5d63ce7c894f2a6b4ca3c996899a4241691373df81c5a0cf1a8ccb','include/linux/compiler_types.h':'4a358c2dcf4079879510c5dcefedfc5f45328e67a406aebb669533fe1146990c'}
FILES={'include/linux/note10_pmu_control_audit.h':'pmu_control_contract.h','drivers/perf/note10_pmu_control_bridge.c':'pmu_control_bridge.c','arch/arm64/kernel/note10_pmu_control_backend.c':'pmu_control_backend.c','kernel/note10_pmu_control_chain.c':'pmu_control_chain.c','kernel/power/note10_pmu_control_capture.c':'pmu_control_capture.c','arch/arm64/mm/note10_pmu_control_probe.c':'pmu_control_probe.c'}
INCLUDES={'drivers/perf/arm_pmu.c':'note10_pmu_control_bridge.c','arch/arm64/kernel/perf_event.c':'note10_pmu_control_backend.c','kernel/cpu_pm.c':'note10_pmu_control_chain.c'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def include(name):return b'\n#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n#include "'+name.encode()+b'"\n#endif\n'
def prepare(source,prior):
 source=Path(source);changed=set(INCLUDES)|{'kernel/note10_pm_pre_chain.c','kernel/power/note10_pm_pre_capture.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','kernel/power/Kconfig'}
 for n,d in PINS.items():
  data=(source/n).read_bytes()
  if n=='include/linux/perf/arm_pmu.h':
   addition=b'\n#ifdef CONFIG_NOTE10_PMU_FAILURE_RESTORE\n\tbool n10_failure_valid, n10_failure_pending;\n\tstruct perf_event *n10_failure_events[ARMPMU_MAX_HWEVENTS];\n#endif\n'
   if data.count(addition)!=1 or sha(data.replace(addition,b'',1))!=d or sha(data)!=prior['pmu_state_snapshot_sha256'][n]:raise ValueError('PMU header reverse pin differs')
  elif sha(data)!=d:raise ValueError('pinned PMU control source differs: '+n)
 before={n:sha((source/n).read_bytes()) for n in changed}
 for n,d in before.items():
  expected=PINS[n] if n=='arch/arm64/kernel/perf_event.c' else prior['pmu_state_snapshot_sha256'][n]
  if d!=expected:raise ValueError('v41 source differs: '+n)
 for target,name in FILES.items():
  p=source/target
  if p.exists():raise ValueError('control helper exists: '+target)
  p.write_bytes((HERE/name).read_bytes())
 for target,name in INCLUDES.items():
  p=source/target;p.write_bytes(p.read_bytes()+include(name))
 p=source/'kernel/note10_pm_pre_chain.c';raw=p.read_bytes();anchor=b'#include <linux/note10_pm_preconditions.h>';raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n#include <linux/string.h>\n#include <linux/note10_pmu_control_audit.h>\n#endif')
 anchor=b'    struct notifier_block *n; unsigned long flags; unsigned int i;';raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n    struct n10_ctl_stage ctl_stage={0};\n#endif')
 anchor=b'        r=&out->row[out->count++];r->priority=READ_ONCE(n->priority);';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n        out->error=n10_ctl_consider(n,&ctl_stage,out->count,generation);\n        if (out->error) goto unlock;\n#endif\n'+anchor)
 anchor=b'unlock:\n    spin_unlock_irqrestore(&cpu_pm_notifier_chain.lock,flags);';raw=replace(raw,anchor,b'unlock:\n#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n    if (!out->error) {\n        if (ctl_stage.count!=1 || ctl_stage.index>=out->count || out->row[ctl_stage.index].kind!=N10_PRE_PMU) out->error=-EIO;\n        else out->error=n10_ctl_resolve(&ctl_stage,out->count,generation);\n    }\n    memzero_explicit(&ctl_stage,sizeof(ctl_stage));\n#endif\n    spin_unlock_irqrestore(&cpu_pm_notifier_chain.lock,flags);');p.write_bytes(raw)
 p=source/'kernel/power/note10_pm_pre_capture.c';raw=p.read_bytes();anchor=b'static struct n10_precond_sample n10_pre_last;';raw=replace(raw,anchor,include('note10_pmu_control_capture.c')+anchor)
 anchor=b'        if (!n10_pre_bad) n10_pre_bad=-EPERM;return -EPERM;';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n        n10_ctl_invalidate();\n#endif\n'+anchor)
 anchor=b'            if (!n10_pre_bad)n10_pre_bad=-EIO;return -EIO; }';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n            n10_ctl_invalidate();\n#endif\n'+anchor)
 anchor=b'    s->error=n10_pre_chain(s,generation);s->completed=1;';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n    n10_ctl_begin(generation);\n#endif\n'+anchor)
 anchor=b'    return s->error;\n}\nint n10_pre_read';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n    n10_ctl_finish(s->error);\n#endif\n'+anchor);p.write_bytes(raw)
 p=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw=p.read_bytes();anchor=b'static bool n10_timer_done;';raw=replace(raw,anchor,anchor+include('note10_pmu_control_probe.c'))
 anchor=b'    int result, error = 0, i;';raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n    bool control_reported=false;\n#endif')
 anchor=b'    status = 0;\nreport:';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n    control_reported=true;\n    if (n10_report_pmu_control(pm.qgeneration,0)) goto report;\n#endif\n'+anchor+b'\n#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n    if (status && !control_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())\n        (void)n10_report_pmu_control(pm.qgeneration,-EIO);\n#endif');p.write_bytes(raw)
 p=source/'kernel/power/Kconfig';p.write_bytes(p.read_bytes()+b'\nconfig NOTE10_PMU_CONTROL_AUDIT\n\tbool "Experimental CPU0 PMU control observation"\n\tdepends on NOTE10_PMU_STATE_AUDIT && NOTE10_GIC_PRIORITY_RESTORE && NOTE10_PMU_FAILURE_RESTORE && NOTE10_CPU_PM_PRECONDITIONS && NOTE10_CPU_PM_BRANCH_AUDIT\n\tdefault n\n')
 return {'pmu_control_audit':True,'pmu_control_audit_version':1,'pmu_control_intermediate_sha256':before,'pmu_control_prepared_sha256':{n:sha((source/n).read_bytes()) for n in sorted(changed|set(FILES))}}
def snapshot(source,out,report):
 source=Path(source);out=Path(out)
 if out.exists():raise ValueError('control snapshot exists')
 names=set(report['pmu_state_snapshot_sha256'])|set(report['pmu_control_prepared_sha256'])|set(PINS)
 for n in sorted(names):
  p=source/n
  if p.is_symlink() or not p.is_file():raise ValueError('invalid source: '+n)
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 return {n:sha((out/n).read_bytes()) for n in sorted(names)}
