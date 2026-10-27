"""Read-only ABOX state/event observations; preserve normal callback results."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
PINS={'sound/soc/samsung/abox/abox.c': '234bd815a338929053473c1c3e05a52c210cc53af41f23449279b3d870610ef0', 'sound/soc/samsung/abox/abox.h': '6173915f547134a66aff5827afa91930ea6ef6c09a344c7bad9d39a3a3a01d15'}
SOURCES=('abox_pm_contract.h','abox_pm_backend.c','abox_pm_probe.c','prepare_abox_pm.py','decode_abox_pm.py','abox_pm_binding.py')
ENABLE_EVENT=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(dev, 1, ret);\n#endif\n'
BEGIN_EVENT=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(dev, 2, 0);\n#endif\n'
END_EVENT=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(dev, 4, 0);\n#endif\n'
IPC_OLD=b'\tif (state != CALLIOPE_DISABLED)\n\t\tabox_cpu_pm_ipc(data, false);'
IPC_EVENT=b'\tif (state != CALLIOPE_DISABLED) {\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\t\tint n10_ipc_ret = abox_cpu_pm_ipc(data, false);\n\t\tn10_abox_note(dev, 3, n10_ipc_ret);\n#else\n\t\tabox_cpu_pm_ipc(data, false);\n#endif\n\t}'

WORK_BEGIN=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(dev, 5, 0);\n#endif\n'
WORK_GET=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\t{ int n10_ret = pm_runtime_get_sync(dev); n10_abox_note(dev, 6, n10_ret); }\n#else\n\tpm_runtime_get_sync(dev);\n#endif'
WORK_GATE=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_can = abox_can_calliope_ipc(dev, data);\n\tn10_abox_note(dev, 7, n10_can);\n\tif (n10_can) {\n#else\n\tif (abox_can_calliope_ipc(dev, data)) {\n#endif'
WORK_END=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(dev, 8, 0);\n#endif\n'
QUEUE_PUT=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(&data->pdev->dev, 9, ret);\n#endif\n'
QUEUE_GET=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(&data->pdev->dev, 10, ret);\n#endif\n'
EVENT_BLOCKS=(ENABLE_EVENT,BEGIN_EVENT,IPC_EVENT,END_EVENT,WORK_BEGIN,WORK_GET,WORK_GATE,WORK_END,QUEUE_PUT,QUEUE_GET)

def event_digest():return hashlib.sha256(b''.join(EVENT_BLOCKS)).hexdigest()

def instrument(raw):
    if hashlib.sha256(raw).hexdigest()!=PINS['sound/soc/samsung/abox/abox.c']:raise ValueError('Pinned ABOX source differs')
    start=raw.index(b'static int abox_enable(struct device *dev)')
    middle=raw.index(b'static int abox_disable(struct device *dev)',start)
    end=raw.index(b'static int abox_runtime_suspend(',middle)
    enable=raw[start:middle];disable=raw[middle:end]
    if enable.count(b'error:\n\treturn ret;')!=1 or disable.count(IPC_OLD)!=1 or disable.count(b'\treturn 0;')!=1:raise ValueError('ABOX event insertion differs')
    enable=enable.replace(b'error:\n\treturn ret;',b'error:\n'+ENABLE_EVENT+b'\treturn ret;')
    disable=disable.replace(b'\tdev_info(dev, "%s\\n", __func__);',BEGIN_EVENT+b'\tdev_info(dev, "%s\\n", __func__);')
    if BEGIN_EVENT not in disable:raise ValueError('ABOX begin event insertion differs')
    disable=disable.replace(IPC_OLD,IPC_EVENT).replace(b'\treturn 0;',END_EVENT+b'\treturn 0;')
    patched=raw[:start]+enable+disable+raw[end:]
    start=patched.index(b'static void abox_process_ipc(struct work_struct *work)')
    end=patched.index(b'static int abox_schedule_ipc(',start)
    worker=patched[start:end]
    if worker.count(b'\tpm_runtime_get_sync(dev);')!=1 or worker.count(b'\tif (abox_can_calliope_ipc(dev, data)) {')!=1 or worker.count(b'\tpm_runtime_put_autosuspend(dev);')!=1:raise ValueError('ABOX worker recipe differs')
    worker=worker.replace(b'\tint ret;',b'\tint ret;\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tbool n10_can;\n#endif')
    worker=worker.replace(b'\tpm_runtime_get_sync(dev);',WORK_BEGIN+WORK_GET)
    worker=worker.replace(b'\tif (abox_can_calliope_ipc(dev, data)) {',WORK_GATE)
    worker=worker.replace(b'\tpm_runtime_put_autosuspend(dev);',b'\tpm_runtime_put_autosuspend(dev);\n'+WORK_END)
    patched=patched[:start]+worker+patched[end:]
    for name,following,block in ((b'static int abox_ipc_queue_put(',b'static int abox_ipc_queue_get(',QUEUE_PUT),(b'static int abox_ipc_queue_get(',b'static bool abox_can_calliope_ipc(',QUEUE_GET)):
        start=patched.index(name);end=patched.index(following,start);section=patched[start:end]
        anchor=b'\tspin_unlock_irqrestore(lock, flags);\n\n\treturn ret;'
        if section.count(anchor)!=1:raise ValueError('ABOX queue return recipe differs')
        section=section.replace(anchor,b'\tspin_unlock_irqrestore(lock, flags);\n'+block+b'\n\treturn ret;')
        patched=patched[:start]+section+patched[end:]
    return b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n#include <linux/note10_abox_pm.h>\n#endif\n'+patched+b'\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n#include "note10_abox_pm.c"\n#endif\n'

PATCHED_SHA='688aafe4befc61e1475dfc1c01054cd99f579ba2c628dbcee34354fe8fa491d8'

def prepare(source):
    source=Path(source)
    for name,digest in PINS.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('Pinned ABOX input differs')
    driver=source/'sound/soc/samsung/abox/abox.c';helper=driver.with_name('note10_abox_pm.c')
    if helper.exists():raise ValueError('ABOX observer already prepared')
    patched=instrument(driver.read_bytes())
    if hashlib.sha256(patched).hexdigest()!=PATCHED_SHA:raise ValueError('ABOX prepared callback binding differs')
    driver.write_bytes(patched);helper.write_bytes((HERE/'abox_pm_backend.c').read_bytes())
    (source/'include/linux/note10_abox_pm.h').write_bytes((HERE/'abox_pm_contract.h').read_bytes())
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';worker.with_name('note10_abox_pm_probe.c').write_bytes((HERE/'abox_pm_probe.c').read_bytes())
    raw=worker.read_bytes();old=b'    status = 0;\nreport:'
    if raw.count(old)!=1:raise ValueError('ABOX report insertion differs')
    worker.write_bytes(b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n#include "note10_abox_pm_probe.c"\n#endif\n'+raw.replace(old,b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n    n10_report_abox_pm(pm.qgeneration);\n#endif\n'+old))
    config=source/'kernel/power/Kconfig';config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_ABOX_PM_AUDIT\n\tbool "Experimental read-only ABOX driver and callback observations"\n\tdepends on NOTE10_IOMMU_PM_AUDIT && SND_SOC_SAMSUNG_ABOX=y\n\tdefault n\n')
    return dict(abox_pm_audit_diagnostic=True,abox_pm_audit_evidence_version=2,abox_pm_source_pins=PINS,abox_patched_sha256=PATCHED_SHA,
        abox_pm_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},audio_dsp_shutdown_verified=False)
