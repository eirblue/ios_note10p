"""Instrument only the pinned opt-in PM devices test; guard low-level entry."""
import hashlib
from pathlib import Path

SUSPEND_SHA='0a845e8ff80474410957cdf0581698889ceeb701795ffbc526aa4cfd70c6f6f3'
HERE=Path(__file__).resolve().parent


def patch_suspend(raw):
    if hashlib.sha256(raw).hexdigest()!=SUSPEND_SHA:raise ValueError('Pinned suspend source differs')
    text=raw.decode()
    changes=[
        ('#include "power.h"', '#include "power.h"\n#include <linux/note10_pm_contract.h>\n'
         'static struct task_struct *n10_pm_owner;\nstatic struct n10_pm_result *n10_pm_active;'),
        ('static int enter_state(suspend_state_t state)\n{\n\tint error;',
         'static int enter_state(suspend_state_t state)\n{\n\tint error;\n\tbool n10_test = false;\n\tint n10_old_level = TEST_NONE;'),
        ('\tif (!mutex_trylock(&pm_mutex))\n\t\treturn -EBUSY;',
         '\tif (!mutex_trylock(&pm_mutex))\n\t\treturn -EBUSY;\n'
         '\tif (n10_pm_active) {\n'
         '\t\tif (n10_pm_owner != current) { error = -EBUSY; goto Unlock; }\n'
         '\t\tn10_old_level = pm_test_level;\n\t\tn10_pm_active->old_level = n10_old_level;\n'
         '\t\tif (n10_old_level != TEST_NONE) { error = -EBUSY; goto Unlock; }\n'
         '\t\tpm_test_level = TEST_DEVICES;\n\t\tn10_test = true;\n\t}'),
        ('\tif (suspend_test(TEST_DEVICES))\n\t\tgoto Recover_platform;',
         '\tif (suspend_test(TEST_DEVICES)) {\n\t\tif (n10_pm_active) ++n10_pm_active->devices;\n'
         '\t\tgoto Recover_platform;\n\t}'),
        ('\t\terror = suspend_enter(state, &wakeup);',
         '\t\tif (n10_pm_active) {\n\t\t\t++n10_pm_active->blocked;\n'
         '\t\t\terror = -EPERM;\n\t\t\tgoto Resume_devices;\n\t\t}\n'
         '\t\terror = suspend_enter(state, &wakeup);'),
        ('\tdpm_resume_end(PMSG_RESUME);',
         '\tdpm_resume_end(PMSG_RESUME);\n\tif (n10_pm_active) ++n10_pm_active->resumed;'),
        (' Unlock:\n\tmutex_unlock(&pm_mutex);',
         ' Unlock:\n\tif (n10_test)\n\t\tpm_test_level = n10_old_level;\n'
         '\tif (n10_pm_active && n10_pm_owner == current)\n'
         '\t\tn10_pm_active->new_level = pm_test_level;\n\tmutex_unlock(&pm_mutex);')]
    for old,new in changes:
        if text.count(old)!=1:raise ValueError('Unexpected PM instrumentation insertion point')
        text=text.replace(old,new)
    return (text+'\n#include "note10_pm_devices_backend.c"\n').encode()


def prepare(source):
    path=source/'kernel/power/suspend.c'
    patched=patch_suspend(path.read_bytes())
    targets={source/'include/linux/note10_pm_contract.h':HERE/'pm_test_contract.h',
             path.with_name('note10_pm_devices_backend.c'):HERE/'pm_devices_backend.c'}
    if any(p.exists() for p in targets):raise ValueError('Existing PM diagnostic extension')
    for target,original in targets.items():target.write_bytes(original.read_bytes())
    path.write_bytes(patched)
    return {'pm_timer_diagnostic':True,'pm_timer_evidence_version':1,'boot_binding_evidence_version':1,
        'pm_timer_source_sha256':hashlib.sha256((HERE/'pm_timer_roundtrip.c').read_bytes()).hexdigest(),
        'pm_backend_source_sha256':hashlib.sha256((HERE/'pm_devices_backend.c').read_bytes()).hexdigest(),
        'pm_contract_sha256':hashlib.sha256((HERE/'pm_test_contract.h').read_bytes()).hexdigest(),
        'patched_suspend_sha256':hashlib.sha256(patched).hexdigest()}
