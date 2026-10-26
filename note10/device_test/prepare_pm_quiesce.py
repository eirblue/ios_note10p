"""Pin and prepare opt-in normal DECON/USB quiescence before devices-only PM."""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    "fs/sync.c": "5e9126c3eb384962baca2ed535a64329ee856e839fb7ff26946daa16154b28c9",
    "drivers/usb/notify/usb_notify.c": "1023decd354d011794f6a1010babcdf46ea4edc705c116af5a07d3447b810ca3",
    "drivers/usb/notify/usb_notifier.c": "c39ec018885b611ea9fc8caff23df6d1e8c19f20d46b410109f6840fd20c07f6",
    "drivers/usb/notify/Kconfig": "c46d7458ce23c535d0601ed027c224b3e8815d532f18952b3bde48a798e673cc",
    "drivers/usb/dwc3/dwc3-exynos.c": "a3a5ca9c2d2614ce5516cd35cb57b9c2837fe4ea79c5189ecad12909b0d85fad",
    "drivers/usb/dwc3/core.c": "7d12e2d8303388da50de6c6631943921562423b4ae35b88d2a1431b668a3a4e1",
    "drivers/usb/dwc3/otg.c": "f8ca1ef72d8eaef9e9377b6ebb6b26bc12c8290d0b502a18bc8fc191017d12de",
    "drivers/usb/dwc3/otg.h": "861157acc947aefeca38f654c3fdcbb382d797b6edef2790ecb99587ee51fdc1",
    "drivers/usb/dwc3/dwc3-exynos.h": "bc9321bdbfb5c44863329dcc66492ebebd952614c1f41b7e4a1e35f9e7672d9e",
    "drivers/usb/dwc3/Kconfig": "5540e7d1a8a01c71de9e8584c12462d319a69e9f6f3ac5e841cfe0b64de2b4c0",
    "include/linux/usb_notify.h": "d32f4f387f8e20373139f6193d974b7b6003568adcec17d1dd094ebd0dd6003c",
    "kernel/power/Kconfig": "80131c416d9e90cc92eedc1cb4111a440eb9ccd4b7428bce6c5c4af02e829cd4",
}
DPU = "drivers/video/fbdev/exynos/dpu20/"
DPU_CORE_PIN = "88899aa623e35a1f0a76b6571bc514691a0d876db7eb17b4c6553a3dfbfb7816"
DPU_HEADER_PIN = "7a99fd3dd6846759f4a0a1ca5d586e52d5123835ba705159b9b82bc17504a56c"


def _replace_once(text, old, new, label):
    if text.count(old) != 1:
        raise ValueError("Unexpected pinned insertion point: " + label)
    return text.replace(old, new)


def _replace_in_function(text, signature, old, new, label):
    """Replace within one function body; duplicate anchors elsewhere are irrelevant."""
    start = text.find(signature)
    if start < 0 or text.find(signature, start + 1) >= 0:
        raise ValueError("Unexpected function anchor: " + label)
    # The next top-level function starts at column zero. Keep the edit bounded.
    end = text.find("\n}", start)
    if end < 0:
        raise ValueError("Unterminated function: " + label)
    body = text[start:end + 2]
    if body.count(old) != 1:
        raise ValueError("Unexpected function-local insertion point: " + label)
    return text[:start] + body.replace(old, new) + text[end + 2:]


def _prepare_usb(source):
    notify_path = source / "drivers/usb/notify/usb_notify.c"
    notify = notify_path.read_text()
    notify = _replace_once(notify, 'int set_notify_disable(struct usb_notify_dev *udev, int disable)\n{',
        '#ifdef CONFIG_NOTE10_PM_QUIESCE\n#include <linux/note10_pm_contract.h>\nstatic int n10_usb_policy_enter(void);\nstatic void n10_usb_policy_exit(void);\nstatic void n10_usb_quiesce_physical(unsigned long event);\n#endif\nint set_notify_disable(struct usb_notify_dev *udev, int disable)\n{', 'USB policy prototypes')
    notify = _replace_in_function(notify, 'int set_notify_disable(struct usb_notify_dev *udev, int disable)\n{',
        '\tint usb_notify_state;', '\tint usb_notify_state;\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n\tint n10_policy_ret = n10_usb_policy_enter();\n\tif (n10_policy_ret) return n10_policy_ret;\n#endif', 'USB policy ownership')
    notify = _replace_in_function(notify, 'int set_notify_disable(struct usb_notify_dev *udev, int disable)\n{',
        '\treturn 0;', '#ifdef CONFIG_NOTE10_PM_QUIESCE\n\tn10_usb_policy_exit();\n#endif\n\treturn 0;', 'USB policy release')
    notify = _replace_in_function(notify, 'void send_otg_notify(struct otg_notify *n,',
        '\ttype = check_event_type(event);', '#ifdef CONFIG_NOTE10_PM_QUIESCE\n\tn10_usb_quiesce_physical(event);\n#endif\n\ttype = check_event_type(event);', 'USB physical epoch')
    helper_path = notify_path.with_name('note10_pm_usb_quiesce.c')
    if helper_path.exists(): raise ValueError('Existing USB helper')
    helper_path.write_bytes((HERE / 'usb_notify_quiesce.c').read_bytes())
    notify += '\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n#include "note10_pm_usb_quiesce.c"\n#endif\n'
    notify_path.write_bytes(notify.encode())
    exynos_path = source / 'drivers/usb/dwc3/dwc3-exynos.c'
    exynos = exynos_path.read_text()
    exynos = _replace_once(exynos, '#include <linux/workqueue.h>', '#include <linux/workqueue.h>\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n#include "core.h"\n#include "otg.h"\n#include <linux/pm_runtime.h>\n#endif', 'USB check headers')
    exynos += r"""
#ifdef CONFIG_NOTE10_PM_QUIESCE
/* Only this controller's worker is observed; no unbounded global flush. */
static int n10_exynos_usb_quiesce_state(bool off, bool resuspend)
{
    struct device_node *np;
    struct platform_device *pdev;
    struct dwc3_exynos *exynos;
    struct otg_fsm *fsm;
    struct dwc3_otg *dotg;
    int ret = -ENODEV;
    np = of_find_compatible_node(NULL, NULL, "samsung,exynos-dwusb");
    if (!np) return ret;
    pdev = of_find_device_by_node(np);
    of_node_put(np);
    if (!pdev) return ret;
    exynos = dev_get_drvdata(&pdev->dev);
    if (!exynos || !exynos->rsw.fsm) goto out;
    fsm = exynos->rsw.fsm;
    dotg = container_of(fsm, struct dwc3_otg, fsm);
    ret = -EAGAIN;
    if (work_busy(&exynos->rsw.work) || !mutex_trylock(&fsm->lock)) goto out;
    if (!mutex_trylock(&dotg->lock)) { mutex_unlock(&fsm->lock); goto out; }
    ret = -EBUSY;
    /* System PM resumes the core into runtime-active state. Re-establish
     * runtime idle only after the owned peripheral/PHY OFF predicates hold.
     * The ordinary request respects runtime references and callback errors.
     */
    if (resuspend && off && dotg->ready && fsm->id && !fsm->reset &&
        dotg->otg.state == OTG_STATE_B_IDLE && !fsm->b_sess_vld &&
        !dotg->dwc->vbus_state && !wake_lock_active(&dotg->wakelock) &&
        dotg->combo_phy_control == 0 && !pm_runtime_suspended(dotg->dwc->dev)) {
        ret = pm_runtime_suspend(dotg->dwc->dev);
        if (ret < 0) goto unlock;
        ret = -EBUSY;
    }
    if (dotg->ready && fsm->id && !fsm->reset &&
        ((off && dotg->otg.state == OTG_STATE_B_IDLE && !fsm->b_sess_vld &&
          !dotg->dwc->vbus_state && pm_runtime_suspended(dotg->dwc->dev) && !wake_lock_active(&dotg->wakelock) &&
          dotg->combo_phy_control == 0) ||
         (!off && dotg->otg.state == OTG_STATE_B_PERIPHERAL && fsm->b_sess_vld &&
          dotg->dwc->vbus_state && pm_runtime_active(dotg->dwc->dev) && wake_lock_active(&dotg->wakelock) &&
          dotg->combo_phy_control == 1))) ret = 0;
unlock:
    mutex_unlock(&dotg->lock);
    mutex_unlock(&fsm->lock);
out:
    put_device(&pdev->dev);
    return ret;
}
int n10_exynos_usb_quiesce_check(bool off)
{
    return n10_exynos_usb_quiesce_state(off, false);
}
int n10_exynos_usb_quiesce_after_pm(void)
{
    return n10_exynos_usb_quiesce_state(true, true);
}
#endif
"""
    exynos_path.write_bytes(exynos.encode())
    otg_path = source / 'drivers/usb/dwc3/otg.c'
    otg = otg_path.read_text()
    otg = _replace_once(otg, '#include "otg.h"', '#include "otg.h"\n#ifdef CONFIG_NOTE10_PM_QUIESCE\nextern bool n10_usb_quiesce_off_requested(void);\nextern void n10_usb_quiesce_transition_error(int error);\nextern bool n10_usb_quiesce_owned(void);\nextern void n10_usb_quiesce_phy_error(bool off, int error);\n#endif', 'USB diagnostic prototypes')
    otg = _replace_in_function(otg, 'static int dwc3_otg_start_gadget(struct otg_fsm *fsm, int on)',
        '\tint ret = 0;', '\tint ret = 0;\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n\tbool n10_owned_off = !on && n10_usb_quiesce_off_requested();\n\tint n10_gadget_error = 0;\n#endif', 'USB owned OFF latch')
    otg = _replace_once(otg, '\t\t\treturn ret;\n\t\t}\n\t\tret = usb_gadget_vbus_disconnect(otg->gadget);',
        '\t\t\t#ifdef CONFIG_NOTE10_PM_QUIESCE\n\t\t\tif (n10_owned_off) {\n\t\t\t\tn10_usb_quiesce_transition_error(-ETIMEDOUT);\n\t\t\t\treturn -ETIMEDOUT;\n\t\t\t}\n\t\t\t#endif\n\t\t\treturn ret;\n\t\t}\n\t\tret = usb_gadget_vbus_disconnect(otg->gadget);', 'USB owned disconnect timeout')
    otg = _replace_in_function(otg, 'static int dwc3_otg_start_gadget(struct otg_fsm *fsm, int on)',
        '\t\tret = usb_gadget_vbus_disconnect(otg->gadget);',
        '\t\tret = usb_gadget_vbus_disconnect(otg->gadget);\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n\t\tif (n10_owned_off) n10_gadget_error = ret;\n#endif', 'USB gadget error capture')
    otg = _replace_in_function(otg, 'static int dwc3_otg_start_gadget(struct otg_fsm *fsm, int on)',
        '\n\treturn ret;', '\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n\tif (n10_owned_off) {\n\t\tif (!ret && n10_gadget_error) ret = n10_gadget_error;\n\t\tif (ret) n10_usb_quiesce_transition_error(ret);\n\t}\n#endif\n\treturn ret;', 'USB final gadget error propagation')
    otg = _replace_in_function(otg, 'int dwc3_otg_phy_enable(struct otg_fsm *fsm, int owner, bool on)',
        '\t\t\tpm_runtime_get_sync(dev);',
        '\t\t\t#ifdef CONFIG_NOTE10_PM_QUIESCE\n\t\t\tif (n10_usb_quiesce_owned()) {\n\t\t\t\tint n10_runtime_ret = pm_runtime_get_sync(dev);\n\t\t\t\tif (n10_runtime_ret < 0) {\n\t\t\t\t\tn10_usb_quiesce_phy_error(!on, n10_runtime_ret);\n\t\t\t\t\tpm_runtime_put_noidle(dev);\n\t\t\t\t\tif (!dotg->pm_qos_int_val) pm_qos_update_request(&dotg->pm_qos_int_req, 0);\n\t\t\t\t\tphy_conn(dwc->usb2_generic_phy, 0);\n\t\t\t\t\tret = n10_runtime_ret;\n\t\t\t\t\tgoto out;\n\t\t\t\t}\n\t\t\t} else\n\t\t\t#endif\n\t\t\tpm_runtime_get_sync(dev);', 'USB runtime get evidence')
    otg = _replace_in_function(otg, 'int dwc3_otg_phy_enable(struct otg_fsm *fsm, int owner, bool on)',
        '\t\t\tpm_runtime_put_sync_suspend(dev);',
        '\t\t\t#ifdef CONFIG_NOTE10_PM_QUIESCE\n\t\t\tif (n10_usb_quiesce_owned()) {\n\t\t\t\tint n10_runtime_ret = pm_runtime_put_sync_suspend(dev);\n\t\t\t\tif (n10_runtime_ret < 0) n10_usb_quiesce_phy_error(!on, n10_runtime_ret);\n\t\t\t} else\n\t\t\t#endif\n\t\t\tpm_runtime_put_sync_suspend(dev);', 'USB runtime put evidence')
    otg = _replace_in_function(otg, 'void dwc3_otg_check_bus_act(struct dwc3 *dwc)',
        '\t} while (--retries);', '\t} while (--retries);\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n\tif (!retries && n10_usb_quiesce_owned())\n\t\tn10_usb_quiesce_phy_error(true, -ETIMEDOUT);\n#endif', 'USB bus activity evidence')
    otg_path.write_bytes(otg.encode())
    return helper_path


def prepare(source, screen_report=None):
    source = Path(source)
    hashes = {}
    for name, expected in PINS.items():
        raw = (source / name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if expected and digest != expected:
            raise ValueError("Pinned USB/PM source differs: " + name)
        hashes[name] = digest
    dcore = source / (DPU + "decon_core.c")
    dheader = source / (DPU + "decon.h")
    if screen_report:
        expected = screen_report.get("screen_log_patched_sha256", {})
        for name, path in ((DPU + "decon_core.c", dcore), (DPU + "decon.h", dheader)):
            if expected.get(name) != hashlib.sha256(path.read_bytes()).hexdigest():
                raise ValueError("Screen preparation output pin differs: " + name)
    else:
        if hashlib.sha256(dcore.read_bytes()).hexdigest() != DPU_CORE_PIN or hashlib.sha256(dheader.read_bytes()).hexdigest() != DPU_HEADER_PIN:
            raise ValueError("Pinned DECON source differs")
    sync = (source / "fs/sync.c").read_text()
    if "pm_get_wakeup_count" not in sync:
        raise ValueError("Pinned interruptible-sync wakeup guard differs")
    helper = source / (DPU + "note10_pm_decon_quiesce.c")
    if helper.exists(): raise ValueError("Existing DECON quiesce extension")
    helper.write_bytes((HERE / "pm_decon_quiesce.c").read_bytes())
    core = dcore.read_text()
    core = _replace_once(core, "int _decon_disable(struct decon_device *decon, enum decon_state state)\n{",
        "#ifdef CONFIG_NOTE10_PM_QUIESCE\nbool n10_decon_quiesce_owned(void);\n#endif\nint _decon_disable(struct decon_device *decon, enum decon_state state)\n{", "DECON ownership prototype")
    core = _replace_in_function(core, "int _decon_disable(struct decon_device *decon, enum decon_state state)\n{", "\tint idle_status = 0;", "\tint idle_status = 0;\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n\tint n10_stop_error = 0;\n#endif", "DECON stop-error local")
    core = _replace_in_function(core, "int _decon_disable(struct decon_device *decon, enum decon_state state)\n{", 'if (idle_status < 0)\n\t\tdecon_err("DECON:ERR:%s:decon is not idle status\\n", __func__);',
        'if (idle_status < 0) {\n\t\tdecon_err("DECON:ERR:%s:decon is not idle status\\n", __func__);\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n\t\tif (n10_decon_quiesce_owned()) return idle_status;\n#endif\n\t}', "DECON idle-error propagation")
    core = _replace_in_function(core, "int _decon_disable(struct decon_device *decon, enum decon_state state)\n{", 'if (ret < 0)\n\t\tdecon_dump(decon, REQ_DSI_DUMP);',
        'if (ret < 0) {\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n\t\tif (n10_decon_quiesce_owned()) n10_stop_error = ret;\n#endif\n\t\tdecon_dump(decon, REQ_DSI_DUMP);\n\t}', "DECON stop-error capture")
    core = _replace_in_function(core, "int _decon_disable(struct decon_device *decon, enum decon_state state)\n{",
        '\n\tret = decon_set_out_sd_state(decon, state);',
        '\n\tret = decon_set_out_sd_state(decon, state);\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n\tif (n10_stop_error && !ret) ret = n10_stop_error;\n#endif', "DECON output-state error preservation")
    core = _replace_in_function(core, "int _decon_disable(struct decon_device *decon, enum decon_state state)\n{", '\tif (diff_time >= 10000000)\n\t\tBUG();',
        '\tif (diff_time >= 10000000) {\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n\t\tif (n10_decon_quiesce_owned()) return -ETIMEDOUT;\n#endif\n\t\tBUG();\n\t}', "DECON owned timeout policy")
    if '#include "note10_pm_decon_quiesce.c"' in core: raise ValueError("DECON helper already included")
    if "#include <linux/note10_pm_contract.h>" not in core:
        core = _replace_once(core, '#include "decon.h"',
            '#include "decon.h"\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n#include <linux/note10_pm_contract.h>\n#include <linux/note10_pm_quiesce.h>\n#endif',
            "DECON quiesce contract includes")
    core += '\n#ifdef CONFIG_NOTE10_PM_QUIESCE\n#include "note10_pm_decon_quiesce.c"\n#endif\n'
    dcore.write_text(core, encoding="utf-8", errors="surrogateescape", newline="\n")
    usb_helper = _prepare_usb(source)
    kconfig = source / "kernel/power/Kconfig"
    kt = kconfig.read_text()
    if "config NOTE10_PM_QUIESCE" in kt: raise ValueError("Quiesce Kconfig already exists")
    kt += """\nconfig NOTE10_PM_QUIESCE
\tbool \"Experimental owned DECON and USB quiesce before devices-only PM test\"
\tdepends on PM_SLEEP && SUSPEND && PM_DEBUG && EXYNOS_DPU20
\tdepends on USB_NOTIFY_LAYER=y && USB_NOTIFIER=y
\tdepends on USB_DWC3=y && USB_DWC3_EXYNOS=y
\tdefault n
\thelp
\t  Reversibly quiesce the built-in DSI display and USB peripheral before
\t  the existing devices-only PM test. This does not enable low-level sleep.
"""
    kconfig.write_text(kt, encoding="utf-8", newline="\n")
    return {"pm_quiesce_diagnostic": True, "pm_quiesce_evidence_version": 1,
            "pm_quiesce_sources_sha256": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                for name in ("prepare_pm_quiesce.py", "pm_quiesce_core.h", "pm_devices_backend.c",
                    "pm_test_contract.h", "pm_decon_quiesce.c", "usb_notify_quiesce.c")},
            "pm_quiesce_source_pins": PINS, "pm_quiesce_upstream_sha256": hashes,
            "pm_quiesce_contract_sha256": hashlib.sha256((HERE / "pm_quiesce_core.h").read_bytes()).hexdigest(),
            "pm_quiesce_backend_sha256": hashlib.sha256((HERE / "pm_devices_backend.c").read_bytes()).hexdigest(),
            "pm_quiesce_decon_helper_sha256": hashlib.sha256(helper.read_bytes()).hexdigest(),
            "pm_quiesce_usb_helper_sha256": hashlib.sha256(usb_helper.read_bytes()).hexdigest(),
            "pm_quiesce_patched_sha256": {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                for name in (DPU + "decon_core.c", DPU + "note10_pm_decon_quiesce.c",
                    "drivers/usb/notify/usb_notify.c", "drivers/usb/notify/note10_pm_usb_quiesce.c",
                    "drivers/usb/dwc3/dwc3-exynos.c", "drivers/usb/dwc3/otg.c", "kernel/power/Kconfig")},
            "interruptible_sync_guard_preserved": True,
            "low_level_suspend_unchanged": True, "xnu_execution": False}
