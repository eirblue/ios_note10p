"""Compose the CPU0 PMU software observation over the exact v40 tree."""
import hashlib, shutil
from pathlib import Path
from prepare_pm_callbacks import HERE, replace
FILES={'include/linux/note10_pmu_state_audit.h':'pmu_state_contract.h','drivers/perf/note10_pmu_state_pmu.c':'pmu_state_pmu.c','kernel/note10_pmu_state_chain.c':'pmu_state_chain.c','kernel/power/note10_pmu_state_capture.c':'pmu_state_capture.c','arch/arm64/mm/note10_pmu_state_probe.c':'pmu_state_probe.c'}
INCLUDES={'drivers/perf/arm_pmu.c':'note10_pmu_state_pmu.c','kernel/cpu_pm.c':'note10_pmu_state_chain.c'}
PIN='0c53ebaed164b0825e78116d26611b837b67b6b44fb42735d13c54645de91f47'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def include(name):return b'\n#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT\n#include "'+name.encode()+b'"\n#endif\n'
def prepare(source,prior):
 source=Path(source); changed=set(INCLUDES)|{'kernel/note10_pm_pre_chain.c','kernel/power/note10_pm_pre_capture.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','kernel/power/Kconfig'}
 before={n:sha((source/n).read_bytes()) for n in changed}
 for n,d in before.items():
  if d!=prior['gic_priority_snapshot_sha256'][n]:raise ValueError('v40 source differs: '+n)
 if sha((source/'include/linux/perf_event.h').read_bytes())!=PIN:raise ValueError('perf event source differs')
 for target,name in FILES.items():
  p=source/target
  if p.exists():raise ValueError('state helper exists: '+target)
  p.write_bytes((HERE/name).read_bytes())
 for target,name in INCLUDES.items():
  p=source/target;p.write_bytes(p.read_bytes()+include(name))
 p=source/'kernel/note10_pm_pre_chain.c';raw=p.read_bytes();anchor=b'#include <linux/note10_pm_preconditions.h>';raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT\n#include <linux/note10_pmu_state_audit.h>\n#endif')
 anchor=b'        n=rcu_dereference_raw(n->next);';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT\n        out->error=n10_state_collect(n,out->count-1,r->kind,generation);\n        if (out->error) break;\n#endif\n'+anchor);p.write_bytes(raw)
 p=source/'kernel/power/note10_pm_pre_capture.c';raw=p.read_bytes();anchor=b'static struct n10_precond_sample n10_pre_last;';raw=replace(raw,anchor,include('note10_pmu_state_capture.c')+anchor)
 anchor=b'        if (!n10_pre_bad) n10_pre_bad=-EPERM;return -EPERM;';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT\n        n10_state_invalidate();\n#endif\n'+anchor)
 anchor=b'            if (!n10_pre_bad)n10_pre_bad=-EIO;return -EIO; }';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT\n            n10_state_invalidate();\n#endif\n'+anchor)
 anchor=b'    s->error=n10_pre_chain(s,generation);s->completed=1;';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT\n    n10_state_begin(generation);\n#endif\n'+anchor)
 anchor=b'    return s->error;\n}\nint n10_pre_read';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT\n    n10_state_finish(s->error);\n#endif\n'+anchor);p.write_bytes(raw)
 p=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw=p.read_bytes();anchor=b'static bool n10_timer_done;';raw=replace(raw,anchor,anchor+include('note10_pmu_state_probe.c'))
 anchor=b'    int result, error = 0, i;';raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT\n    bool state_reported=false;\n#endif')
 anchor=b'    status = 0;\nreport:';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT\n    state_reported=true;\n    if (n10_report_pmu_state(pm.qgeneration,0)) goto report;\n#endif\n'+anchor+b'\n#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT\n    if (status && !state_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())\n        (void)n10_report_pmu_state(pm.qgeneration,-EIO);\n#endif');p.write_bytes(raw)
 p=source/'kernel/power/Kconfig';p.write_bytes(p.read_bytes()+b'\nconfig NOTE10_PMU_STATE_AUDIT\n\tbool "Experimental CPU0 PMU software state audit"\n\tdepends on NOTE10_GIC_PRIORITY_RESTORE && NOTE10_CPU_PM_BRANCH_AUDIT && NOTE10_CPU_PM_PRECONDITIONS && NOTE10_PMU_FAILURE_RESTORE\n\tdefault n\n')
 final={n:sha((source/n).read_bytes()) for n in sorted(changed|set(FILES))}
 return {'pmu_state_audit':True,'pmu_state_audit_version':1,'pmu_state_intermediate_sha256':before,'pmu_state_prepared_sha256':final}
def snapshot(source,out,report):
 source=Path(source);out=Path(out)
 if out.exists():raise ValueError('state snapshot exists')
 names=set(report['gic_priority_snapshot_sha256'])|set(report['pmu_state_prepared_sha256'])|{'include/linux/perf_event.h'}
 for n in sorted(names):
  src=source/n
  if src.is_symlink() or not src.is_file():raise ValueError('invalid source: '+n)
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 return {n:sha((out/n).read_bytes()) for n in sorted(names)}
