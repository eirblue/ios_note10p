"""Opt-in late/noirq dry run; never disable CPUs, run syscore or enter sleep."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE_SHA='d9e4a9e8e23188c0ca1758993066ed06c379b19d35c67ae40bc0f6eada77a947'
FINAL_SHA='2bad7dc2695559e4df992a6571fb2c79cc4879384819f946254da4519049efde'
PINS={
 'drivers/base/power/domain.c':'ffdab65add339e2b2fe61e338b59880d34bb8017323a924dd0f093a24eea850a',
 'include/linux/suspend.h':'aab32391cdfe66aad03175b64f263021a43a2665152acc3001edfba2c419f005',
 'drivers/soc/samsung/exynos-pm.c':'b3c0b39bab253f70374f2912169da8cf9490b25cec12719137defd386548ee95',
}
SOURCES=('test_pm_noirq_pmu_native.py','pm_noirq_contract.h','pm_noirq_backend.c','pm_noirq_probe.c','prepare_pm_noirq.py','decode_pm_noirq.py','pm_noirq_binding.py')
CALL_GUARD=b'\t\tif (n10_pm_active) {\n\t\t\t++n10_pm_active->blocked;\n\t\t\terror = -EPERM;\n\t\t\tgoto Resume_devices;\n\t\t}'
CALL_EXTEND=b'''\t\tif (n10_pm_active) {
#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST
            n10_pm_noirq_begin(state);
            if (n10_pm_noirq_ready(state)) {
                error = suspend_enter(state, &wakeup);
                error = n10_pm_noirq_finish(error);
                goto Resume_devices;
            }
            n10_pm_noirq_note(8, -EPERM);
            n10_pm_noirq_finish(-EPERM);
#endif
\t\t\t++n10_pm_active->blocked;
\t\t\terror = -EPERM;
\t\t\tgoto Resume_devices;
\t\t}'''

def replace(raw,old,new):
    if raw.count(old)!=1:raise ValueError('Noirq composition insertion differs')
    return raw.replace(old,new)

def instrument(raw):
    if hashlib.sha256(raw).hexdigest()!=BASE_SHA:raise ValueError('Guarded DMA suspend base differs')
    raw=replace(raw,b'\t\tpm_test_level = TEST_DEVICES;',b'#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n\t\tpm_test_level = TEST_PLATFORM;\n#else\n\t\tpm_test_level = TEST_DEVICES;\n#endif')
    raw=replace(raw,b'\tif (suspend_test(TEST_DEVICES)) {',b'#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n    if (n10_pm_active && n10_pm_owner == current && pm_test_level == TEST_PLATFORM)\n        ++n10_pm_active->devices;\n#endif\n\tif (suspend_test(TEST_DEVICES)) {')
    raw=replace(raw,CALL_GUARD,CALL_EXTEND)
    raw=replace(raw,b'\tif (!sleep_state_supported(state))\n\t\treturn -ENOSYS;',b'#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n    if (n10_pm_active && !n10_pm_noirq_context(state)) return -EPERM;\n#endif\n\tif (!sleep_state_supported(state))\n\t\treturn -ENOSYS;')
    raw=replace(raw,b'\terror = platform_suspend_prepare(state);',b'#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n    if (n10_pm_active && !n10_pm_noirq_ready(state)) return -EPERM;\n#endif\n\terror = platform_suspend_prepare(state);')
    for name,begin,end in [('late',2,3),('noirq',4,5)]:
        call=('\terror = dpm_suspend_'+name+'(PMSG_SUSPEND);').encode()
        before=('#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n    if (n10_pm_active) n10_pm_noirq_note('+str(begin)+', 0);\n#endif\n').encode()
        after=('\n#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n    if (n10_pm_active) n10_pm_noirq_note('+str(end)+', error);\n#endif').encode()
        raw=replace(raw,call,before+call+after)
    raw=replace(raw,b'\tif (suspend_test(TEST_PLATFORM))\n\t\tgoto Platform_wake;',b'''\tif (suspend_test(TEST_PLATFORM)) {
#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST
        if (n10_pm_active) n10_pm_noirq_note(6, 0);
#endif
\t\tgoto Platform_wake;
    }
#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST
    /* Diagnostic owner must never reach CPU disable, syscore or machine entry. */
    if (n10_pm_active) {
        n10_pm_noirq_note(8, -EPERM);
        ++n10_pm_active->blocked;
        error = -EPERM;
        goto Platform_wake;
    }
#endif''')
    prefix=b'#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n#include <linux/note10_pm_noirq.h>\n#endif\n'
    suffix=b'\n#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n#include "note10_pm_noirq.c"\n#endif\n'
    return prefix+raw+suffix

def prepare(source):
    source=Path(source)
    for name,digest in PINS.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('Noirq prerequisite source differs: '+name)
    p=source/'kernel/power/suspend.c';base=p.read_bytes();raw=instrument(base)
    if hashlib.sha256(raw).hexdigest()!=FINAL_SHA:raise ValueError('Final noirq composition differs')
    p.with_name('suspend-base.c').write_bytes(base)
    p.write_bytes(raw);p.with_name('note10_pm_noirq.c').write_bytes((HERE/'pm_noirq_backend.c').read_bytes())
    (source/'include/linux/note10_pm_noirq.h').write_bytes((HERE/'pm_noirq_contract.h').read_bytes())
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';worker.with_name('note10_pm_noirq_probe.c').write_bytes((HERE/'pm_noirq_probe.c').read_bytes())
    text=replace(worker.read_bytes(),b'    status = 0;\nreport:',b'#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n    n10_report_pm_noirq(pm.qgeneration);\n#endif\n    status = 0;\nreport:')
    worker.write_bytes(b'#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n#include "note10_pm_noirq_probe.c"\n#endif\n'+text)
    k=source/'kernel/power/Kconfig';k.write_bytes(k.read_bytes()+b'\nconfig NOTE10_PM_NOIRQ_TEST\n\tbool "Experimental guarded device late/noirq dry run"\n\tdepends on NOTE10_ABOX_PMU_AUDIT && PM_DEBUG && SUSPEND\n\tdefault n\n')
    return dict(pm_noirq_diagnostic=True,pm_noirq_evidence_version=1,pm_noirq_source_pins=PINS,pm_noirq_base_suspend_sha256=BASE_SHA,
                pm_noirq_final_suspend_sha256=FINAL_SHA,patched_suspend_sha256=FINAL_SHA,
                pm_noirq_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES})
