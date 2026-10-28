"""Compose read-only RCU context observation over exact v43 source."""
import hashlib,shutil
from pathlib import Path
from prepare_pm_callbacks import HERE,replace
PINS={'kernel/rcu/tree.c':'e869c5e723d9046dc6ffe6f18f308a0a8e2a712edc7acaaf26f5eeafff8f80b7','kernel/rcu/tree.h':'c649ce7b8e5d3dcaf623a6d2f69b57c4237234f9636dca8fbadaa3129df0c203','include/linux/sched.h':'ed3501d62e5a8afc1d76480155285321474b6958ffbccd01cd06cd8d7ffab0a3','kernel/rcu/update.c':'e8c4ac7ac401de0bdc0307c077fef51578ad450472f92bcd5a642e798acb136b','include/linux/kernel.h':'5c8c7992db241ca1c2c8127752f82e8d56acb5a2b0f6c1532533c5af05639fc0','kernel/rcu/Makefile':'99dbcf158de3dbf355cab2778094880fd6f5de7a2ac03a94febba70b75243682'}
FILES={'include/linux/note10_rcu_context_audit.h':'rcu_context_contract.h','kernel/rcu/note10_rcu_context_getter.c':'rcu_context_getter.c','kernel/note10_rcu_context_chain.c':'rcu_context_chain.c','kernel/power/note10_rcu_context_capture.c':'rcu_context_capture.c','arch/arm64/mm/note10_rcu_context_probe.c':'rcu_context_probe.c'}
CHANGED=('kernel/rcu/tree.c','kernel/cpu_pm.c','kernel/note10_pm_pre_chain.c','kernel/power/note10_pm_pre_capture.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','kernel/power/Kconfig')
def sha(x):return hashlib.sha256(x).hexdigest()
def include(name):return b'\n#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT\n#include "'+name.encode()+b'"\n#endif\n'
def prepare(source,prior):
 source=Path(source)
 for name,digest in PINS.items():
  if sha((source/name).read_bytes())!=digest:raise ValueError('pinned RCU source differs: '+name)
 before={n:sha((source/n).read_bytes()) for n in CHANGED}
 if any(before[n]!=(PINS[n] if n=='kernel/rcu/tree.c' else prior['fpsimd_reference_snapshot_sha256'][n]) for n in CHANGED):raise ValueError('prior source differs')
 for target,name in FILES.items():
  p=source/target
  if p.exists():raise ValueError('RCU helper exists: '+target)
  p.write_bytes((HERE/name).read_bytes())
 for name,helper in (('kernel/rcu/tree.c','note10_rcu_context_getter.c'),('kernel/cpu_pm.c','note10_rcu_context_chain.c')):
  p=source/name;p.write_bytes(p.read_bytes()+include(helper))
 p=source/'kernel/note10_pm_pre_chain.c';raw=p.read_bytes();anchor=b'#include <linux/note10_pm_preconditions.h>';raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT\n#include <linux/note10_rcu_context_audit.h>\n#endif')
 anchor=b'    spin_unlock_irqrestore(&cpu_pm_notifier_chain.lock,flags);';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT\n    if (!out->error) out->error=n10_rcu_collect(out,generation);\n#endif\n'+anchor);p.write_bytes(raw)
 p=source/'kernel/power/note10_pm_pre_capture.c';raw=p.read_bytes();anchor=b'static struct n10_precond_sample n10_pre_last;';raw=replace(raw,anchor,include('note10_rcu_context_capture.c')+anchor)
 for anchor in (b'        if (!n10_pre_bad) n10_pre_bad=-EPERM;return -EPERM;',b'            if (!n10_pre_bad)n10_pre_bad=-EIO;return -EIO; }'):
  raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT\n            n10_rcu_invalidate();\n#endif\n'+anchor)
 anchor=b'    s->error=n10_pre_chain(s,generation);s->completed=1;';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT\n    n10_rcu_begin(generation);\n#endif\n'+anchor)
 anchor=b'    return s->error;\n}\nint n10_pre_read';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT\n    n10_rcu_finish(s->error);\n#endif\n'+anchor);p.write_bytes(raw)
 p=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw=p.read_bytes();anchor=b'static bool n10_timer_done;';raw=replace(raw,anchor,anchor+include('note10_rcu_context_probe.c'))
 anchor=b'    int result, error = 0, i;';raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT\n    bool rcu_reported=false;\n#endif')
 anchor=b'    status = 0;\nreport:';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT\n    rcu_reported=true;\n    if (n10_report_rcu_context(pm.qgeneration,0)) goto report;\n#endif\n'+anchor+b'\n#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT\n    if (status && !rcu_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())\n        (void)n10_report_rcu_context(pm.qgeneration,-EIO);\n#endif');p.write_bytes(raw)
 p=source/'kernel/power/Kconfig';p.write_bytes(p.read_bytes()+b'\nconfig NOTE10_RCU_CONTEXT_AUDIT\n\tbool "Experimental CPU0 RCU context observation"\n\tdepends on PREEMPT_RCU && NOTE10_FPSIMD_REFERENCE_AUDIT && NOTE10_CPU_PM_PRECONDITIONS\n\tdefault n\n')
 return {'rcu_context_audit':True,'rcu_context_audit_version':1,'rcu_context_intermediate_sha256':before,'rcu_context_prepared_sha256':{n:sha((source/n).read_bytes()) for n in sorted(set(CHANGED)|set(FILES))}}
def snapshot(source,out,report):
 source=Path(source);out=Path(out)
 if out.exists():raise ValueError('RCU snapshot exists')
 names=set(report['fpsimd_reference_snapshot_sha256'])|set(report['rcu_context_prepared_sha256'])|set(PINS)
 for n in sorted(names):
  p=source/n
  if p.is_symlink() or not p.is_file():raise ValueError('invalid source: '+n)
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 return {n:sha((out/n).read_bytes()) for n in sorted(names)}
