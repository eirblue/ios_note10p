"""Read-only DMA-capable device PM framework coverage on pinned device lists."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
PIN='77535e2d086fcd23afaffac6d789605ef40a3398249dc9f6cb6593d6417192e1'
SOURCES=('dma_pm_backend.c','dma_pm_probe.c','dma_pm_contract.h','prepare_dma_pm.py','decode_dma_pm.py','dma_pm_binding.py')

def replace(text,old,new):
    if text.count(old)!=1:raise ValueError('Pinned DMA PM insertion point differs')
    return text.replace(old,new)

def prepare(source):
    source=Path(source);main=source/'drivers/base/power/main.c'
    if hashlib.sha256(main.read_bytes()).hexdigest()!=PIN:raise ValueError('Pinned device PM core differs')
    helper=main.with_name('note10_dma_pm.c')
    if helper.exists():raise ValueError('DMA PM audit already prepared')
    helper.write_bytes((HERE/'dma_pm_backend.c').read_bytes())
    (source/'include/linux/note10_dma_pm.h').write_bytes((HERE/'dma_pm_contract.h').read_bytes())
    main.write_bytes(main.read_bytes()+b'\n#ifdef CONFIG_NOTE10_DMA_PM_AUDIT\n#include "note10_dma_pm.c"\n#endif\n')
    suspend=source/'kernel/power/suspend.c';text=suspend.read_bytes()
    text=replace(text,b'#include <linux/note10_pm_contract.h>',b'#include <linux/note10_pm_contract.h>\n#ifdef CONFIG_NOTE10_DMA_PM_AUDIT\n#include <linux/note10_dma_pm.h>\n#endif')
    guard=b'n10_pm_active && n10_pm_owner == current'
    def capture(phase,condition=b''):
        return b'\n#ifdef CONFIG_NOTE10_DMA_PM_AUDIT\n\tif ('+condition+guard+b') n10_dma_pm_capture('+str(phase).encode()+b', n10_pm_active->qgeneration);\n#endif\n'
    text=replace(text,b'\terror = dpm_suspend_start(PMSG_SUSPEND);',capture(0)+b'\terror = dpm_suspend_start(PMSG_SUSPEND);'+capture(1,b'!error && '))
    text=replace(text,b'\tdpm_resume_end(PMSG_RESUME);',b'\tdpm_resume_end(PMSG_RESUME);'+capture(2))
    suspend.write_bytes(text)
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';text=worker.read_bytes()
    worker.with_name('note10_dma_pm_probe.c').write_bytes((HERE/'dma_pm_probe.c').read_bytes())
    worker.write_bytes(b'#ifdef CONFIG_NOTE10_DMA_PM_AUDIT\n#include "note10_dma_pm_probe.c"\n#endif\n'+replace(text,b'    status = 0;\nreport:',b'#ifdef CONFIG_NOTE10_DMA_PM_AUDIT\n    n10_report_dma_pm(pm.qgeneration);\n#endif\n    status = 0;\nreport:'))
    config=source/'kernel/power/Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_DMA_PM_AUDIT\n\tbool "Experimental read-only DMA-capable device PM coverage audit"\n\tdepends on NOTE10_PM_QUIESCE && NOTE10_GIC_ROUNDTRIP\n\tdefault n\n')
    return dict(dma_pm_audit_diagnostic=True,dma_pm_audit_evidence_version=1,
        dma_pm_audit_source_pin=PIN,dma_pm_audit_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
        dma_pm_audit_patched_sha256={str(p.relative_to(source)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in (main,suspend,worker)},
        dma_shutdown_verified=False)
