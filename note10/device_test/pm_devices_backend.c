/* SPDX-License-Identifier: GPL-2.0-only */
/* Included at the end of pinned kernel/power/suspend.c, opt-in only. */
#ifdef CONFIG_NOTE10_SCREEN_LOG
extern int n10_screen_pause(bool paused);
#endif
#ifdef CONFIG_NOTE10_PM_QUIESCE
extern int n10_decon_quiesce_begin(struct n10_pm_result *out);
extern int n10_decon_quiesce_end(struct n10_pm_result *out);
extern int n10_usb_quiesce_begin(struct n10_pm_result *out);
extern int n10_usb_quiesce_end(struct n10_pm_result *out);
extern int n10_usb_quiesce_validate(void);
#endif
int n10_pm_devices_test(struct n10_pm_result *out)
{
    int ret = 0;
#if defined(CONFIG_NOTE10_PM_QUIESCE) || defined(CONFIG_NOTE10_SCREEN_LOG)
    int restore_ret;
#endif
    bool owner = false;
#ifdef CONFIG_NOTE10_SCREEN_LOG
    bool screen_paused = false;
#endif
#ifdef CONFIG_NOTE10_PM_QUIESCE
    bool decon_touched = false, usb_touched = false;
    unsigned int wake_count = 0;
#endif
    if (!out)
        return -EINVAL;
    mutex_lock(&pm_mutex);
    if (n10_pm_owner || n10_pm_active) {
        mutex_unlock(&pm_mutex);
        return -EBUSY;
    }
    memset(out, 0, sizeof(*out));
    out->stage = 1;
    out->resume_errors_before = suspend_stats.failed_resume;
    n10_pm_owner = current;
    n10_pm_active = out;
    owner = true;
#ifdef CONFIG_NOTE10_PM_QUIESCE
    out->qphase = N10_Q_OWNER;
#endif
    mutex_unlock(&pm_mutex);

#ifdef CONFIG_NOTE10_SCREEN_LOG
    screen_paused = true;
    ret = n10_screen_pause(true);
    if (ret) { out->screen_error = ret; goto restore; }
#endif
#ifdef CONFIG_NOTE10_PM_QUIESCE
    decon_touched = true;
    ret = n10_decon_quiesce_begin(out);
    if (ret) { out->display_error = ret; goto restore; }
    out->qphase = N10_Q_DISPLAY_OFF;
    usb_touched = true;
    ret = n10_usb_quiesce_begin(out);
    if (ret) { out->usb_error = ret; goto restore; }
    out->qphase = N10_Q_USB_BLOCKED;
    if (!pm_get_wakeup_count(&wake_count, false)) {
        pm_print_active_wakeup_sources();
        ret = -EBUSY;
        out->wake_error = ret;
        goto restore;
    }
    ret = n10_usb_quiesce_validate();
    if (ret) { out->usb_error = ret; goto restore; }
    out->qphase = N10_Q_WAKE_CLEAR;
#endif
    out->pm_called = 1;
#ifdef CONFIG_NOTE10_PM_QUIESCE
    out->qphase = N10_Q_PM_ENTERED;
#endif
    out->error = pm_suspend(PM_SUSPEND_MEM);
    ret = out->error;
#ifdef CONFIG_NOTE10_PM_QUIESCE
    restore_ret = n10_usb_quiesce_validate();
    if (restore_ret) { out->usb_error = restore_ret; if (!ret) ret = restore_ret; }
#endif
restore:
    /* Always unwind in reverse order; retain every restore result. */
#ifdef CONFIG_NOTE10_PM_QUIESCE
    if (usb_touched) {
        restore_ret = n10_usb_quiesce_end(out);
        out->usb_restore_error = restore_ret;
        if (restore_ret && !ret) ret = restore_ret;
    }
    if (decon_touched) {
        restore_ret = n10_decon_quiesce_end(out);
        out->display_restore_error = restore_ret;
        if (restore_ret && !ret) ret = restore_ret;
    }
#endif
#ifdef CONFIG_NOTE10_SCREEN_LOG
    if (screen_paused) {
        restore_ret = n10_screen_pause(false);
        out->screen_restore_error = restore_ret;
        if (restore_ret && !ret) ret = restore_ret;
    }
#endif
#ifdef CONFIG_NOTE10_PM_QUIESCE
    out->quiesce_restored = !out->usb_restore_error &&
        !out->display_restore_error && !out->screen_restore_error;
#endif
    mutex_lock(&pm_mutex);
    out->resume_errors_after = suspend_stats.failed_resume;
    if (owner && n10_pm_active == out && n10_pm_owner == current) {
        n10_pm_active = NULL;
        n10_pm_owner = NULL;
    } else if (!ret) {
        ret = -EOWNERDEAD;
    }
#ifdef CONFIG_NOTE10_PM_QUIESCE
    out->qphase = out->quiesce_restored ? N10_Q_DONE : N10_Q_FAILED;
#endif
    mutex_unlock(&pm_mutex);
    if (ret && !out->error) out->error = ret;
    return ret;
}
