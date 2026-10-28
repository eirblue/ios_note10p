"""Compose the v45 EHLD lock-availability audit over the immutable v44 tree."""
import hashlib
import shutil
from pathlib import Path
from prepare_pm_callbacks import HERE, replace

FILES = {
    'include/linux/note10_ehld_lock_audit.h': 'ehld_lock_contract.h',
    'drivers/soc/samsung/debug/note10_ehld_lock_getter.c': 'ehld_lock_getter.c',
    'kernel/note10_ehld_lock_chain.c': 'ehld_lock_chain.c',
    'kernel/power/note10_ehld_lock_capture.c': 'ehld_lock_capture.c',
    'arch/arm64/mm/note10_ehld_lock_probe.c': 'ehld_lock_probe.c',
}
CHANGED = (
    'drivers/soc/samsung/debug/exynos-ehld.c', 'kernel/cpu_pm.c',
    'kernel/note10_pm_pre_chain.c', 'kernel/power/note10_pm_pre_capture.c',
    'arch/arm64/mm/note10_pm_timer_roundtrip.c', 'kernel/power/Kconfig',
)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def inc(name):
    return b'\n#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT\n#include "' + name.encode() + b'"\n#endif\n'

def prepare(source, prior):
    source = Path(source)
    before = {n: sha((source / n).read_bytes()) for n in CHANGED}
    for name, digest in prior['rcu_context_snapshot_sha256'].items():
        if name in before and before[name] != digest:
            raise ValueError('v44 composed source differs: ' + name)
    for target, name in FILES.items():
        p = source / target
        if p.exists():
            raise ValueError('EHLD lock helper already exists: ' + target)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((HERE / name).read_bytes())

    p = source / 'drivers/soc/samsung/debug/exynos-ehld.c'
    p.write_bytes(p.read_bytes() + inc('note10_ehld_lock_getter.c'))
    p = source / 'kernel/cpu_pm.c'
    p.write_bytes(p.read_bytes() + inc('note10_ehld_lock_chain.c'))

    p = source / 'kernel/note10_pm_pre_chain.c'
    raw = p.read_bytes()
    anchor = b'#include <linux/note10_pm_preconditions.h>'
    raw = replace(raw, anchor, anchor + b'\n#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT\n#include <linux/note10_ehld_lock_audit.h>\n#endif')
    anchor = b'        n=rcu_dereference_raw(n->next);'
    raw = replace(raw, anchor, b'#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT\n        out->error=n10_ehld_lock_collect(n,out,out->count-1,generation);\n        if (out->error) break;\n#endif\n' + anchor)
    anchor = b'unlock:\n#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT'
    raw = replace(raw, anchor, b'unlock:\n#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT\n    if (!out->error) out->error=n10_ehld_lock_complete(out,generation);\n#endif\n#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT')
    p.write_bytes(raw)

    p = source / 'kernel/power/note10_pm_pre_capture.c'
    raw = p.read_bytes()
    anchor = b'#include <linux/note10_pm_preconditions.h>'
    raw = replace(raw, anchor, anchor + b'\n#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT\n#include "note10_ehld_lock_capture.c"\n#endif')
    for anchor in (b'        if (!n10_pre_bad) n10_pre_bad=-EPERM;return -EPERM;',
                   b'            if (!n10_pre_bad)n10_pre_bad=-EIO;return -EIO; }'):
        raw = replace(raw, anchor, b'#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT\n            n10_ehld_lock_invalidate();\n#endif\n' + anchor)
    anchor = b'    s->error=n10_pre_chain(s,generation);s->completed=1;'
    raw = replace(raw, anchor, b'#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT\n    n10_ehld_lock_begin(generation);\n#endif\n' + anchor)
    anchor = b'    return s->error;\n}\nint n10_pre_read'
    raw = replace(raw, anchor, b'#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT\n    n10_ehld_lock_finish(s->error);\n#endif\n' + anchor)
    p.write_bytes(raw)

    p = source / 'arch/arm64/mm/note10_pm_timer_roundtrip.c'
    raw = p.read_bytes()
    anchor = b'static bool n10_timer_done;'
    raw = replace(raw, anchor, anchor + inc('note10_ehld_lock_probe.c'))
    anchor = b'    int result, error = 0, i;'
    raw = replace(raw, anchor, anchor + b'\n#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT\n    bool ehld_lock_reported=false;\n#endif')
    anchor = b'    status = 0;\nreport:'
    raw = replace(raw, anchor, b'#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT\n    ehld_lock_reported=true;\n    if (n10_report_ehld_lock(pm.qgeneration,0)) goto report;\n#endif\n' + anchor + b'\n#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT\n    if (status && !ehld_lock_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())\n        (void)n10_report_ehld_lock(pm.qgeneration,-EIO);\n#endif')
    p.write_bytes(raw)

    p = source / 'kernel/power/Kconfig'
    p.write_bytes(p.read_bytes() + b'\nconfig NOTE10_EHLD_LOCK_AUDIT\n\tbool "Experimental EHLD lock availability observation"\n\tdepends on NOTE10_RCU_CONTEXT_AUDIT && EXYNOS_EHLD && PREEMPT_COUNT\n\tdefault n\n')
    prepared = {n: sha((source / n).read_bytes()) for n in sorted(set(CHANGED) | set(FILES))}
    return {'ehld_lock_audit': True, 'ehld_lock_audit_version': 1,
            'ehld_lock_intermediate_sha256': before,
            'ehld_lock_prepared_sha256': prepared}

def snapshot(source, output, report):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError('EHLD lock snapshot exists')
    names = set(report['rcu_context_snapshot_sha256']) | set(report['ehld_lock_prepared_sha256'])
    for name in sorted(names):
        p = source / name
        if p.is_symlink() or not p.is_file():
            raise ValueError('invalid composed source: ' + name)
        dst = output / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dst)
    return {n: sha((output / n).read_bytes()) for n in sorted(names)}
