/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in exynos-ehld.c; pointer equality only, no event dereference. */
#include <linux/note10_pm_branch.h>
int n10_branch_ehld_equal(const void *event)
{
    struct exynos_ehld_ctrl *c=this_cpu_ptr(&ehld_ctrl);
    return event && event==READ_ONCE(c->event);
}
