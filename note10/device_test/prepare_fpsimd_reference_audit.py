"""Compose FPSIMD reference observation over the exact v42 snapshot."""
import hashlib, shutil
from pathlib import Path
from prepare_pm_callbacks import HERE, replace
FILES = {
    'include/linux/note10_fpsimd_reference_audit.h': 'fpsimd_reference_contract.h',
    'arch/arm64/kernel/note10_fpsimd_reference_getter.c': 'fpsimd_reference_getter.c',
    'kernel/note10_fpsimd_reference_chain.c': 'fpsimd_reference_chain.c',
    'kernel/power/note10_fpsimd_reference_capture.c': 'fpsimd_reference_capture.c',
    'arch/arm64/mm/note10_fpsimd_reference_probe.c': 'fpsimd_reference_probe.c',
}
CHANGED = ('arch/arm64/kernel/fpsimd.c', 'kernel/cpu_pm.c', 'kernel/note10_pm_pre_chain.c', 'kernel/power/note10_pm_pre_capture.c', 'arch/arm64/mm/note10_pm_timer_roundtrip.c', 'kernel/power/Kconfig')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def include(name): return b'\n#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT\n#include "' + name.encode() + b'"\n#endif\n'
def prepare(source, prior):
    source = Path(source)
    before = {n: sha((source/n).read_bytes()) for n in CHANGED}
    if any(before[n] != (prior['pm_preconditions_prepared_sha256'][n] if n == 'arch/arm64/kernel/fpsimd.c' else prior['pmu_control_snapshot_sha256'][n]) for n in CHANGED): raise ValueError('prior snapshot differs')
    for target, name in FILES.items():
        p = source/target
        if p.exists(): raise ValueError('reference helper exists: '+target)
        p.write_bytes((HERE/name).read_bytes())
    for name, helper in (('arch/arm64/kernel/fpsimd.c','note10_fpsimd_reference_getter.c'),('kernel/cpu_pm.c','note10_fpsimd_reference_chain.c')):
        p=source/name; p.write_bytes(p.read_bytes()+include(helper))
    p=source/'kernel/note10_pm_pre_chain.c'; raw=p.read_bytes()
    anchor=b'#include <linux/note10_pm_preconditions.h>'; raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT\n#include <linux/note10_fpsimd_reference_audit.h>\n#endif')
    anchor=b'        n=rcu_dereference_raw(n->next);'; raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT\n        out->error=n10_fps_collect(n,out->count-1,r->kind,generation);\n        if (out->error) break;\n#endif\n'+anchor)
    anchor=b'    spin_unlock_irqrestore(&cpu_pm_notifier_chain.lock,flags);'; raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT\n    if (!out->error) out->error=n10_fps_complete(out,generation);\n#endif\n'+anchor); p.write_bytes(raw)
    p=source/'kernel/power/note10_pm_pre_capture.c';raw=p.read_bytes(); anchor=b'static struct n10_precond_sample n10_pre_last;';raw=replace(raw,anchor,include('note10_fpsimd_reference_capture.c')+anchor)
    for anchor in (b'        if (!n10_pre_bad) n10_pre_bad=-EPERM;return -EPERM;',b'            if (!n10_pre_bad)n10_pre_bad=-EIO;return -EIO; }'):
        raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT\n            n10_fps_invalidate();\n#endif\n'+anchor)
    anchor=b'    s->error=n10_pre_chain(s,generation);s->completed=1;';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT\n    n10_fps_begin(generation);\n#endif\n'+anchor)
    anchor=b'    return s->error;\n}\nint n10_pre_read';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT\n    n10_fps_finish(s->error);\n#endif\n'+anchor);p.write_bytes(raw)
    p=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c'; raw=p.read_bytes();anchor=b'static bool n10_timer_done;';raw=replace(raw,anchor,anchor+include('note10_fpsimd_reference_probe.c'))
    anchor=b'    int result, error = 0, i;';raw=replace(raw,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT\n    bool fps_reported=false;\n#endif')
    anchor=b'    status = 0;\nreport:';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT\n    fps_reported=true;\n    if (n10_report_fpsimd_reference(pm.qgeneration,0)) goto report;\n#endif\n'+anchor+b'\n#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT\n    if (status && !fps_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())\n        (void)n10_report_fpsimd_reference(pm.qgeneration,-EIO);\n#endif');p.write_bytes(raw)
    p=source/'kernel/power/Kconfig';p.write_bytes(p.read_bytes()+b'\nconfig NOTE10_FPSIMD_REFERENCE_AUDIT\n\tbool "Experimental CPU0 FPSIMD reference observation"\n\tdepends on NOTE10_PMU_CONTROL_AUDIT && NOTE10_CPU_PM_PRECONDITIONS\n\tdefault n\n')
    return {'fpsimd_reference_audit':True,'fpsimd_reference_audit_version':1,'fpsimd_reference_intermediate_sha256':before,'fpsimd_reference_prepared_sha256':{n:sha((source/n).read_bytes()) for n in sorted(set(CHANGED)|set(FILES))}}
def snapshot(source,out,report):
    source=Path(source);out=Path(out)
    if out.exists(): raise ValueError('reference snapshot exists')
    names=set(report['pmu_control_snapshot_sha256'])|set(report['pm_preconditions_prepared_sha256'])|set(report['fpsimd_reference_prepared_sha256'])
    for name in sorted(names):
        p=source/name
        if p.is_symlink() or not p.is_file(): raise ValueError('invalid source: '+name)
        dst=out/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
    return {name:sha((out/name).read_bytes()) for name in sorted(names)}
