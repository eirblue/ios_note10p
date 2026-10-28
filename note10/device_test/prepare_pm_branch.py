"""Compose v38 branch observations over the exact v37 prepared tree."""
import hashlib,shutil
from pathlib import Path
from prepare_pm_callbacks import HERE,replace
from prepare_pm_preconditions import PINS as PRE_PINS
FILES={'include/linux/note10_pm_branch.h':'pm_branch_contract.h','drivers/perf/note10_pm_branch_pmu.c':'pm_branch_pmu.c','drivers/soc/samsung/debug/note10_pm_branch_ehld.c':'pm_branch_ehld.c','kernel/note10_pm_branch_chain.c':'pm_branch_chain.c','kernel/power/note10_pm_branch_capture.c':'pm_branch_capture.c','arch/arm64/mm/note10_pm_branch_probe.c':'pm_branch_probe.c'}
INCLUDES={'drivers/perf/arm_pmu.c':'note10_pm_branch_pmu.c','drivers/soc/samsung/debug/exynos-ehld.c':'note10_pm_branch_ehld.c','kernel/cpu_pm.c':'note10_pm_branch_chain.c'}
KCONFIG=b'\nconfig NOTE10_CPU_PM_BRANCH_AUDIT\n\tbool "Experimental CPU0 PM branch observations"\n\tdepends on NOTE10_CPU_PM_PRECONDITIONS\n\tdefault n\n'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def include(name):return b'\n#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT\n#include "'+name.encode()+b'"\n#endif\n'
def prepare(source,prior):
 source=Path(source);prev=prior['pm_preconditions_prepared_sha256'];changed=set(INCLUDES)|{'kernel/note10_pm_pre_chain.c','kernel/power/note10_pm_pre_capture.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','kernel/power/Kconfig'}
 for n in changed:
  if sha((source/n).read_bytes())!=prev[n]:raise ValueError('v37 prepared source differs: '+n)
 intermediate={n:sha((source/n).read_bytes()) for n in changed}
 for target,name in FILES.items():
  p=source/target
  if p.exists():raise ValueError('branch helper exists')
  p.write_bytes((HERE/name).read_bytes())
 for target,name in INCLUDES.items():
  p=source/target;p.write_bytes(p.read_bytes()+include(name))
 chain=source/'kernel/note10_pm_pre_chain.c';raw=chain.read_bytes();anchor=b'#include <linux/note10_pm_preconditions.h>';raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT\n#include <linux/note10_pm_branch.h>\n#endif')
 anchor=b'        n=rcu_dereference_raw(n->next);';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT\n        out->error=n10_branch_collect(n,out->count-1,r->kind);\n        if (out->error) break;\n#endif\n'+anchor);chain.write_bytes(raw)
 cap=source/'kernel/power/note10_pm_pre_capture.c';raw=cap.read_bytes();anchor=b'static struct n10_precond_sample n10_pre_last;';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT\n#include "note10_pm_branch_capture.c"\n#endif\n'+anchor)
 anchor=b'        if (!n10_pre_bad) n10_pre_bad=-EPERM;return -EPERM;';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT\n        n10_branch_invalidate();\n#endif\n'+anchor)
 anchor=b'        if (!delta || delta>=0x80000000U) { if (!n10_pre_bad)n10_pre_bad=-EIO;return -EIO; }';raw=replace(raw,anchor,b'        if (!delta || delta>=0x80000000U) {\n#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT\n            n10_branch_invalidate();\n#endif\n            if (!n10_pre_bad)n10_pre_bad=-EIO;return -EIO; }')
 anchor=b'    s->error=n10_pre_chain(s,generation);s->completed=1;';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT\n    n10_branch_begin(generation);\n#endif\n'+anchor)
 anchor=b'    return s->error;\n}\nint n10_pre_read';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT\n    n10_branch_finish(s->error);\n#endif\n'+anchor);cap.write_bytes(raw)
 worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw=worker.read_bytes();anchor=b'static bool n10_timer_done;';raw=replace(raw,anchor,anchor+include('note10_pm_branch_probe.c'))
 anchor=b'    int result, error = 0, i;';raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT\n    bool branch_reported=false;\n#endif')
 anchor=b'    status = 0;\nreport:';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT\n    branch_reported=true;\n    if (n10_report_pm_branch(pm.qgeneration,0)) goto report;\n#endif\n'+anchor+b'\n#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT\n    if (status && !branch_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())\n        (void)n10_report_pm_branch(pm.qgeneration,-EIO);\n#endif');worker.write_bytes(raw)
 config=source/'kernel/power/Kconfig';config.write_bytes(config.read_bytes()+KCONFIG)
 final={n:sha((source/n).read_bytes()) for n in changed|set(FILES)}
 return {'pm_branch_diagnostic':True,'pm_branch_version':1,'pm_branch_intermediate_sha256':intermediate,'pm_branch_prepared_sha256':final}
def snapshot(source,out,prepared):
 source=Path(source);out=Path(out)
 if out.exists():raise ValueError('branch snapshot exists')
 for name,digest in prepared.items():
  rel=Path(name);src=source/rel
  if rel.is_absolute() or '..' in rel.parts or src.is_symlink() or sha(src.read_bytes())!=digest:raise ValueError('branch snapshot differs')
  dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
