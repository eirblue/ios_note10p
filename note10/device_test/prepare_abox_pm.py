"""Read-only ABOX state/event observations; preserve normal callback results."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
PINS={'sound/soc/samsung/abox/abox.c': '234bd815a338929053473c1c3e05a52c210cc53af41f23449279b3d870610ef0', 'sound/soc/samsung/abox/abox.h': '6173915f547134a66aff5827afa91930ea6ef6c09a344c7bad9d39a3a3a01d15'}
PINS['sound/soc/samsung/abox/abox_core.c']='a70b0a8856c29d3359e6b14ac4c6f64ea6f5bb3c05cef78158d20a68ec7c0508'
SOURCES=('abox_pm_contract.h','abox_pm_backend.c','abox_pm_probe.c','prepare_abox_pm.py','decode_abox_pm.py','abox_pm_binding.py')
PINS.update({'sound/soc/samsung/abox/abox_qos.c':'e396c8e9c82b8ed72b9ea59f1a8b46926e9e8deb98d134726620e26d9f172f78',
    'sound/soc/samsung/abox/abox_qos.h':'107235e3adc1467eb0e9265109212d1341e1f83babfa3fca0b779a7416dc7adc'})
SOURCES=SOURCES+('abox_qos_pm_backend.c',)
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
FW_EVENT=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(dev, 11, ret);\n#endif\n'
NOTIFY_BEGIN=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(dev, 12, 0);\n#endif\n'
NOTIFY_READY=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(dev, 13, 0);\n#endif\n'
NOTIFY_GATE=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_clearable = abox_is_clearable(dev, data);\n\tn10_abox_note(dev, 14, n10_clearable);\n\tif (n10_clearable) {\n#else\n\tif (abox_is_clearable(dev, data)) {\n#endif'
NOTIFY_SUSPEND=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(dev, 15, ret);\n#endif\n'
NOTIFY_BAD=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(dev, 16, 0);\n#endif\n'
NOTIFY_DONE=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tif (action == PM_SUSPEND_PREPARE) n10_abox_note(dev, 17, 0);\n#endif\n'
EVENT_BLOCKS=(ENABLE_EVENT,BEGIN_EVENT,IPC_EVENT,END_EVENT,WORK_BEGIN,WORK_GET,WORK_GATE,WORK_END,QUEUE_PUT,QUEUE_GET,FW_EVENT,NOTIFY_BEGIN,NOTIFY_READY,NOTIFY_GATE,NOTIFY_SUSPEND,NOTIFY_BAD,NOTIFY_DONE)
QOS_GET=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\t{ int n10_ret = pm_runtime_get(dev_abox); n10_abox_note(dev_abox, 18, n10_ret); }\n#else\n\tpm_runtime_get(dev_abox);\n#endif'
QOS_PUT=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\t{ int n10_ret = pm_runtime_put_autosuspend(dev_abox); n10_abox_note(dev_abox, 19, n10_ret); }\n#else\n\tpm_runtime_put_autosuspend(dev_abox);\n#endif'
QOS_WORK_BEGIN=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(dev_abox, 20, 0);\n#endif\n'
QOS_WORK_END=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tn10_abox_note(dev_abox, 21, 0);\n#endif\n'
QOS_PATCHED_SHA='75f3c217b7cc85a2d0a9576e5af0f34c25ffa8a76ef79e1f7dc96f48f3e9448c'
QOS_TARGET_SHA='666d22452848a90e884a6a5d992363658dcf396d7baca3cb7e850f8f796636e2'

PROBE_GET=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n    {\n        int n10_before = atomic_read(&dev->power.usage_count);\n        int n10_ret = pm_runtime_get(dev);\n        int n10_after = atomic_read(&dev->power.usage_count);\n        n10_abox_lifecycle(dev, 0, n10_ret, n10_before, n10_after);\n    }\n#else\n\tpm_runtime_get(dev);\n#endif'
LATE_OLD=b'\tif (p_abox_data && p_abox_data->pdev)\n\t\tpm_runtime_put_sync_suspend(&p_abox_data->pdev->dev);\n\telse\n\t\tpr_err("%s: p_abox_data or pdev is null", __func__);'
LATE_BODY=b'\tif (p_abox_data && p_abox_data->pdev) {\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n        struct device *dev = &p_abox_data->pdev->dev;\n        int n10_before, n10_ret, n10_after;\n        n10_abox_late_state(3);\n        n10_before = atomic_read(&dev->power.usage_count);\n        n10_ret = pm_runtime_put_sync_suspend(dev);\n        n10_after = atomic_read(&dev->power.usage_count);\n        n10_abox_lifecycle(dev, 1, n10_ret, n10_before, n10_after);\n#else\n\t\tpm_runtime_put_sync_suspend(&p_abox_data->pdev->dev);\n#endif\n\t} else {\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n        n10_abox_late_state(p_abox_data ? 2 : 1);\n#endif\n\t\tpr_err("%s: p_abox_data or pdev is null", __func__);\n\t}'

def system_block(call,kind):
    statement=b'pm_runtime_get_noresume(dev);' if kind==2 else b'n10_ret = pm_runtime_put(dev);'
    result=b'0' if kind==2 else b'n10_ret'
    declarations=b'int n10_before, n10_after;' if kind==2 else b'int n10_before, n10_after, n10_ret;'
    return (b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n    {\n        '+declarations+b'\n        n10_before = atomic_read(&dev->power.usage_count);\n        '+statement+
        b'\n        n10_after = atomic_read(&dev->power.usage_count);\n        n10_abox_lifecycle(dev, '+str(kind).encode()+b', '+result+b', n10_before, n10_after);\n    }\n#else\n'+call+b'\n#endif')
SYSTEM_GET=system_block(b'\tpm_runtime_get_noresume(dev);',2)
SYSTEM_PUT=system_block(b'\tpm_runtime_put(dev);',3)
SYSTEM_ERROR_PUT=system_block(b'\t\tpm_runtime_put(dev);',4)
SYSTEM_BLOCKS=(SYSTEM_GET,SYSTEM_PUT,SYSTEM_ERROR_PUT)
SYSTEM_PATCHED_SHA='7418b3f416308b7755b582b7e98199c912997cd566f8decae97259bdcb903419'

def instrument_system(raw):
    from prepare_dma_pm import PIN
    suffix=b'\n#ifdef CONFIG_NOTE10_DMA_PM_AUDIT\n#include "note10_dma_pm.c"\n#endif\n'
    if not raw.endswith(suffix) or hashlib.sha256(raw[:-len(suffix)]).hexdigest()!=PIN:raise ValueError('Pinned prepared PM core differs')
    for old,new in ((b'\tpm_runtime_get_noresume(dev);',SYSTEM_GET),(b'\tpm_runtime_put(dev);',SYSTEM_PUT),(b'\t\tpm_runtime_put(dev);',SYSTEM_ERROR_PUT)):
        # Match whole lines so error rollback cannot be mistaken for complete.
        anchor=b'\n'+old+b'\n'
        if raw.count(anchor)!=1:raise ValueError('PM core reference recipe differs')
        raw=raw.replace(anchor,b'\n'+new+b'\n')
    return b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n#include <linux/note10_abox_pm.h>\n#endif\n'+raw

ASYNC_OLD=b'\tpm_runtime_resume(dev);'
ASYNC_RESUME=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n    n10_abox_async_firmware(dev, !!fw);\n#endif\n#ifdef CONFIG_NOTE10_ABOX_FW_FAILURE_GUARD\n    if (!fw) {\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n        n10_abox_async_skipped(dev);\n#endif\n        return;\n    }\n#endif\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n    {\n        int n10_before, n10_ret, n10_after;\n        n10_before = atomic_read(&dev->power.usage_count);\n        n10_ret = pm_runtime_resume(dev);\n        n10_after = atomic_read(&dev->power.usage_count);\n        n10_abox_lifecycle(dev, 5, n10_ret, n10_before, n10_after);\n    }\n#else\n\tpm_runtime_resume(dev);\n#endif'
CORE_PATCHED_SHA='cd17a9bf0dfef9722ba46afba7cc667928e88b494343b1d04f3eb4be2d4a1283'
def instrument_core(raw):
    if hashlib.sha256(raw).hexdigest()!=PINS['sound/soc/samsung/abox/abox_core.c']:raise ValueError('Pinned ABOX core differs')
    if raw.count(ASYNC_OLD)!=1:raise ValueError('Firmware completion resume recipe differs')
    return b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n#include <linux/note10_abox_pm.h>\n#endif\n'+raw.replace(ASYNC_OLD,ASYNC_RESUME)

def event_digest():return hashlib.sha256(b''.join(EVENT_BLOCKS+SYSTEM_BLOCKS)+(ASYNC_RESUME)+(QOS_GET+QOS_PUT+QOS_WORK_BEGIN+QOS_WORK_END+PROBE_GET+LATE_BODY)).hexdigest()

def instrument_qos(raw):
    if hashlib.sha256(raw).hexdigest()!=PINS['sound/soc/samsung/abox/abox_qos.c']:raise ValueError('Pinned QoS source differs')
    if raw.count(b'\t\t\t\tpm_runtime_get(dev_abox);')!=1 or raw.count(b'\t\t\t\tpm_runtime_put_autosuspend(dev_abox);')!=1:raise ValueError('QoS runtime call insertion differs')
    patched=raw.replace(b'\t\t\t\tpm_runtime_get(dev_abox);',QOS_GET).replace(b'\t\t\t\tpm_runtime_put_autosuspend(dev_abox);',QOS_PUT)
    start=patched.index(b'static void abox_qos_work_func(');end=patched.index(b'static DECLARE_WORK(',start)
    worker=patched[start:end];anchor=b'\tfor (p_qos = abox_qos_array; p_qos - abox_qos_array < len; p_qos++)'
    if worker.count(anchor)!=1 or worker.count(b'\t\tabox_qos_apply(*p_qos);')!=1:raise ValueError('QoS worker event insertion differs')
    worker=worker.replace(anchor,QOS_WORK_BEGIN+anchor).replace(b'\t\tabox_qos_apply(*p_qos);',b'\t\tabox_qos_apply(*p_qos);\n'+QOS_WORK_END)
    patched=patched[:start]+worker+patched[end:]
    return b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n#include <linux/note10_abox_pm.h>\n#endif\n'+patched+b'\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n#include "note10_abox_qos_pm.c"\n#endif\n'

def instrument(raw):
    if hashlib.sha256(raw).hexdigest()!=PINS['sound/soc/samsung/abox/abox.c']:raise ValueError('Pinned ABOX source differs')
    start=raw.index(b'static int abox_enable(struct device *dev)')
    middle=raw.index(b'static int abox_disable(struct device *dev)',start)
    end=raw.index(b'static int abox_runtime_suspend(',middle)
    enable=raw[start:middle];disable=raw[middle:end]
    if enable.count(b'error:\n\treturn ret;')!=1 or disable.count(IPC_OLD)!=1 or disable.count(b'\treturn 0;')!=1:raise ValueError('ABOX event insertion differs')
    enable=enable.replace(b'error:\n\treturn ret;',b'error:\n'+ENABLE_EVENT+b'\treturn ret;')
    anchor=b'\t\tret = abox_download_firmware(dev);'
    if enable.count(anchor)!=1:raise ValueError('ABOX firmware return insertion differs')
    enable=enable.replace(anchor,anchor+b'\n'+FW_EVENT)
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
    start=patched.index(b'static int abox_pm_notifier(');end=patched.index(b'static int abox_modem_notifier(',start)
    notifier=patched[start:end]
    if notifier.count(b'\tint ret;')!=1 or notifier.count(b'\t\tif (abox_is_clearable(dev, data)) {')!=1 or notifier.count(b'\t\t\tret = pm_runtime_suspend(dev);')!=1:raise ValueError('ABOX notifier recipe differs')
    notifier=notifier.replace(b'\tint ret;',b'\tint ret;\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n\tbool n10_clearable;\n#endif')
    notifier=notifier.replace(b'\tcase PM_SUSPEND_PREPARE:',b'\tcase PM_SUSPEND_PREPARE:\n'+NOTIFY_BEGIN)
    notifier=notifier.replace(b'\t\tflush_workqueue(data->ipc_workqueue);',b'\t\tflush_workqueue(data->ipc_workqueue);\n'+NOTIFY_READY)
    notifier=notifier.replace(b'\t\tif (abox_is_clearable(dev, data)) {',NOTIFY_GATE)
    notifier=notifier.replace(b'\t\t\tret = pm_runtime_suspend(dev);',b'\t\t\tret = pm_runtime_suspend(dev);\n'+NOTIFY_SUSPEND)
    notifier=notifier.replace(b'\t\t\t\treturn NOTIFY_BAD;',NOTIFY_BAD+b'\t\t\t\treturn NOTIFY_BAD;')
    notifier=notifier.replace(b'\treturn NOTIFY_DONE;',NOTIFY_DONE+b'\treturn NOTIFY_DONE;')
    if any(notifier.count(block)!=1 for block in (NOTIFY_BEGIN,NOTIFY_READY,NOTIFY_GATE,NOTIFY_SUSPEND,NOTIFY_BAD,NOTIFY_DONE)):raise ValueError('ABOX notifier event insertion differs')
    patched=patched[:start]+notifier+patched[end:]
    if patched.count(b'\tpm_runtime_get(dev);')!=1 or patched.count(LATE_OLD)!=1:raise ValueError('ABOX lifecycle recipe differs')
    patched=patched.replace(b'\tpm_runtime_get(dev);',PROBE_GET).replace(LATE_OLD,LATE_BODY)
    return b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n#include <linux/note10_abox_pm.h>\n#endif\n'+patched+b'\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n#include "note10_abox_pm.c"\n#endif\n'

PATCHED_SHA='703edcd950d2796e8afbd36d4e4e3bfb0884b3b585a41547ca509eee56dfd2ae'

def prepare(source):
    source=Path(source)
    for name,digest in PINS.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('Pinned ABOX input differs')
    core=source/'sound/soc/samsung/abox/abox_core.c'
    core_patched=instrument_core(core.read_bytes())
    if hashlib.sha256(core_patched).hexdigest()!=CORE_PATCHED_SHA:raise ValueError('Prepared firmware callback binding differs')
    core.write_bytes(core_patched)
    main=source/'drivers/base/power/main.c'
    system=instrument_system(main.read_bytes())
    if hashlib.sha256(system).hexdigest()!=SYSTEM_PATCHED_SHA:raise ValueError('Prepared PM core binding differs')
    main.write_bytes(system)
    driver=source/'sound/soc/samsung/abox/abox.c';helper=driver.with_name('note10_abox_pm.c')
    if helper.exists():raise ValueError('ABOX observer already prepared')
    patched=instrument(driver.read_bytes())
    if hashlib.sha256(patched).hexdigest()!=PATCHED_SHA:raise ValueError('ABOX prepared callback binding differs')
    driver.write_bytes(patched);helper.write_bytes((HERE/'abox_pm_backend.c').read_bytes())
    qos=driver.with_name('abox_qos.c');qos_patched=instrument_qos(qos.read_bytes())
    if hashlib.sha256(qos_patched).hexdigest()!=QOS_PATCHED_SHA:raise ValueError('QoS prepared callback binding differs')
    qos.write_bytes(qos_patched);qos.with_name('note10_abox_qos_pm.c').write_bytes((HERE/'abox_qos_pm_backend.c').read_bytes())
    (source/'include/linux/note10_abox_pm.h').write_bytes((HERE/'abox_pm_contract.h').read_bytes())
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';worker.with_name('note10_abox_pm_probe.c').write_bytes((HERE/'abox_pm_probe.c').read_bytes())
    raw=worker.read_bytes();old=b'    status = 0;\nreport:'
    if raw.count(old)!=1:raise ValueError('ABOX report insertion differs')
    worker.write_bytes(b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n#include "note10_abox_pm_probe.c"\n#endif\n'+raw.replace(old,b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n    n10_report_abox_pm(pm.qgeneration);\n#endif\n'+old))
    config=source/'kernel/power/Kconfig';config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_ABOX_PM_AUDIT\n\tbool "Experimental read-only ABOX driver and callback observations"\n\tdepends on NOTE10_IOMMU_PM_AUDIT && SND_SOC_SAMSUNG_ABOX=y\n\tdefault n\n')
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_ABOX_FW_FAILURE_GUARD\n\tbool "Experimental skip of runtime resume after failed ABOX firmware completion"\n\tdepends on NOTE10_ABOX_PM_AUDIT\n\tdefault n\n')
    return dict(abox_failed_fw_resume_guard=True,abox_pm_audit_diagnostic=True,abox_pm_audit_evidence_version=8,abox_core_patched_sha256=CORE_PATCHED_SHA,abox_system_patched_sha256=SYSTEM_PATCHED_SHA,abox_pm_source_pins=PINS,abox_patched_sha256=PATCHED_SHA,abox_qos_patched_sha256=QOS_PATCHED_SHA,
        abox_pm_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},audio_dsp_shutdown_verified=False)
