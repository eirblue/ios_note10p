/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in suspend.c after the guarded noirq reader. */
#include <linux/note10_pmu_settle.h>
int n10_pm_settle_capture(struct n10_pmu_settle_sample *out,
                        unsigned int completed, unsigned int index)
{
    unsigned int following;
    int ret = -EIO;
    if (!out) return -EINVAL;
    memset(out, 0, sizeof(*out));out->completed = completed;out->index = index;out->error = 5;
    if (!completed || index >= 3 || irqs_disabled()) return -EINVAL;
    if (!mutex_trylock(&pm_mutex)) return -EBUSY;
    following = n10_pm_noirq_last.generation + 1;
    if (!following) following = 1;
    if (!n10_pm_owner && !n10_pm_active && pm_test_level == TEST_NONE && following == completed &&
        n10_pm_noirq_last.generation && n10_pm_noirq_last.seen == 1 &&
        !n10_pm_noirq_last.bad && n10_pm_noirq_last.finished == 1 &&
        n10_pm_noirq_last.stage == 7 && n10_pm_noirq_last.state == PM_SUSPEND_MEM &&
        n10_pm_noirq_last.phase == N10_Q_PM_ENTERED &&
        n10_pm_noirq_last.late == 1 && n10_pm_noirq_last.late_ok == 1 &&
        n10_pm_noirq_last.noirq == 1 && n10_pm_noirq_last.noirq_ok == 1 &&
        n10_pm_noirq_last.point == 1 && !n10_pm_noirq_last.blocked &&
        !n10_pm_noirq_last.ops_mask && !n10_pm_noirq_last.error && !n10_pm_noirq_last.original_error &&
        n10_pm_noirq_last.pre_early == n10_pm_noirq_last.post_early &&
        n10_pm_noirq_last.pre_noirq == n10_pm_noirq_last.post_noirq &&
        n10_pm_noirq_last.post_early == READ_ONCE(suspend_stats.failed_resume_early) &&
        n10_pm_noirq_last.post_noirq == READ_ONCE(suspend_stats.failed_resume_noirq))
        ret = n10_pmu_settle_capture(out, completed, index);
    mutex_unlock(&pm_mutex);
    return ret;
}
