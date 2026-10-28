/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in exynos-ehld.c; never dereference the event. */
#include <linux/note10_pm_preconditions.h>
int n10_pre_ehld(struct notifier_block *n, struct n10_precond_row *r)
{
    struct exynos_ehld_ctrl *c;
    if (n != &exynos_ehld_c2_pm_nb || READ_ONCE(n->notifier_call) != exynos_ehld_c2_pm_notifier) return 0;
    c=this_cpu_ptr(&ehld_ctrl);r->valid=3;r->value[0]=READ_ONCE(c->ehld_running);r->value[1]=!!READ_ONCE(c->event);
    return 1;
}
