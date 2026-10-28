/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in cpufreq_schedutil.c; timer linkage read only when started. */
#include <linux/note10_pm_preconditions.h>
int n10_pre_sugov(struct notifier_block *n, struct n10_precond_row *r)
{
    struct sugov_exynos *s;
    if (n != &sugov_pm_nb || READ_ONCE(n->notifier_call) != sugov_pm_notifier) return 0;
    s=this_cpu_ptr(&sugov_exynos);r->valid=3;r->value[0]=READ_ONCE(s->enabled);r->value[1]=READ_ONCE(s->started);
    if (r->value[1]) { r->valid|=4;r->value[2]=!!READ_ONCE(s->timer.entry.pprev); }
    return 1;
}
