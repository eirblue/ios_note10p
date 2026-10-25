/* SPDX-License-Identifier: GPL-2.0-only */
/* Included at the end of pinned kernel/power/suspend.c, opt-in only.
 * enter_state owns test-level changes under pm_mutex. Its diagnostic hooks
 * count device/resume phases and block every low-level suspend attempt.
 */
int n10_pm_devices_test(struct n10_pm_result *out)
{
    if (!out)
        return -EINVAL;
    mutex_lock(&pm_mutex);
    if (n10_pm_owner || n10_pm_active) {
        mutex_unlock(&pm_mutex);
        return -EBUSY;
    }
    memset(out, 0, sizeof(*out));
    out->resume_errors_before = suspend_stats.failed_resume;
    n10_pm_owner = current;
    n10_pm_active = out;
    mutex_unlock(&pm_mutex);

    out->error = pm_suspend(PM_SUSPEND_MEM);

    mutex_lock(&pm_mutex);
    out->resume_errors_after = suspend_stats.failed_resume;
    n10_pm_active = NULL;
    n10_pm_owner = NULL;
    mutex_unlock(&pm_mutex);
    return out->error;
}
