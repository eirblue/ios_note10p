/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in irq-gic.c; identify only, no hardware access. */
#include <linux/note10_pm_preconditions.h>
int n10_pre_gic(struct notifier_block *n, struct n10_precond_row *r)
{ (void)r; return n == &gic_notifier_block && READ_ONCE(n->notifier_call) == gic_notifier; }
