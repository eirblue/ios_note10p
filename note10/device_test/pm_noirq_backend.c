/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in the bound suspend core. PM mutex protects the entire transaction. */
#include <linux/note10_pm_noirq.h>
static struct n10_pm_noirq_sample n10_pm_noirq_last;
static unsigned int n10_pm_noirq_ops_mask(void)
{
    if (!suspend_ops || !suspend_ops->enter) return 16;
    return (!!suspend_ops->prepare) | ((!!suspend_ops->prepare_late) << 1) |
           ((!!suspend_ops->wake) << 2) | ((!!suspend_ops->finish) << 3);
}
static int n10_pm_noirq_owned(void)
{
    return n10_pm_active && n10_pm_owner == current &&
           n10_pm_active->pm_called == 1 &&
           n10_pm_active->qphase == N10_Q_PM_ENTERED &&
           n10_pm_active->qgeneration;
}
void n10_pm_noirq_begin(int state)
{
    struct n10_pm_noirq_sample *s = &n10_pm_noirq_last;
    unsigned int generation;
    if (!n10_pm_noirq_owned()) return;
    generation = n10_pm_active->qgeneration;
    if (s->seen && s->generation == generation) { s->bad = 1; return; }
    memset(s, 0, sizeof(*s));
    s->generation = generation; s->seen = 1; s->stage = 1;
    s->state = state; s->phase = n10_pm_active->qphase;
    s->ops_mask = n10_pm_noirq_ops_mask();
    s->pre_early = READ_ONCE(suspend_stats.failed_resume_early);
    s->pre_noirq = READ_ONCE(suspend_stats.failed_resume_noirq);
    if (suspend_stats.failed_resume_early < 0 || suspend_stats.failed_resume_noirq < 0)
        s->bad = 1;
}
int n10_pm_noirq_context(int state)
{
    return n10_pm_noirq_owned() && !irqs_disabled() && state == PM_SUSPEND_MEM &&
           pm_test_level == TEST_PLATFORM;
}
int n10_pm_noirq_ready(int state)
{
    struct n10_pm_noirq_sample *s = &n10_pm_noirq_last;
    return n10_pm_noirq_context(state) && !n10_pm_noirq_ops_mask() &&
           s->seen == 1 && !s->bad && !s->finished && s->state == (unsigned int)state &&
           s->generation == n10_pm_active->qgeneration;
}
void n10_pm_noirq_note(unsigned int event, int result)
{
    struct n10_pm_noirq_sample *s = &n10_pm_noirq_last;
    if (!n10_pm_noirq_owned()) return;
    if (s->generation != n10_pm_active->qgeneration || s->seen != 1 || s->bad || s->finished) { s->bad = 1; return; }
    s->stage = event;
    switch (event) {
    case 2: if (s->late++) s->bad = 1; break;
    case 3: if (!s->late || s->late_ok || s->noirq) s->bad = 1;
            else if (!result) s->late_ok = 1; break;
    case 4: if (!s->late_ok || s->noirq++) s->bad = 1; break;
    case 5: if (!s->noirq || s->noirq_ok || s->point) s->bad = 1;
            else if (!result) s->noirq_ok = 1; break;
    case 6:
        if (!s->late_ok || !s->noirq_ok || s->point++ || !n10_pm_noirq_ready(PM_SUSPEND_MEM))
            s->bad = 1;
        if (!s->bad) n10_pmu_noirq_capture(s->generation);
        break;
    case 8: ++s->blocked; break;
    default: s->bad = 1; break;
    }
}
int n10_pm_noirq_finish(int result)
{
    struct n10_pm_noirq_sample *s = &n10_pm_noirq_last;
    if (!n10_pm_noirq_owned()) return -EPERM;
    if (s->generation != n10_pm_active->qgeneration || s->seen != 1 || s->finished) { s->bad = 1; return -EIO; }
    s->finished = 1; s->stage = 7; s->original_error = result;
    s->post_early = READ_ONCE(suspend_stats.failed_resume_early);
    s->post_noirq = READ_ONCE(suspend_stats.failed_resume_noirq);
    /* Never let an EBUSY retry hide an earlier late/noirq restoration failure. */
    if (s->pre_early != s->post_early || s->pre_noirq != s->post_noirq) result = -EIO;
    s->error = result;
    return result;
}
int n10_pm_noirq_read(struct n10_pm_noirq_sample *out,
                     struct n10_pmu_noirq_sample *pmu, unsigned int completed)
{
    unsigned int following;
    int ret;
    if (!out || !pmu || !completed || irqs_disabled()) return -EINVAL;
    mutex_lock(&pm_mutex);
    memcpy(out, &n10_pm_noirq_last, sizeof(*out));
    ret = n10_pmu_noirq_read(pmu, completed);
    mutex_unlock(&pm_mutex);
    following = out->generation + 1;
    if (!following) following = 1;
    if (ret || following != completed || !out->generation || out->seen != 1 || out->bad ||
        out->finished != 1 || out->stage != 7 || out->state != PM_SUSPEND_MEM ||
        out->phase != N10_Q_PM_ENTERED || out->late != 1 || out->late_ok != 1 ||
        out->noirq != 1 || out->noirq_ok != 1 || out->point != 1 || out->blocked ||
        out->ops_mask || out->error || out->original_error || out->pre_early != out->post_early ||
        out->pre_noirq != out->post_noirq || pmu->generation != out->generation)
        return -EIO;
    return 0;
}
