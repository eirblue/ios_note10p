/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in arm_arch_timer.c; identify only. */
#include <linux/note10_pm_preconditions.h>
int n10_pre_timer(struct notifier_block *n, struct n10_precond_row *r)
{ (void)r; return n == &arch_timer_cpu_pm_notifier && READ_ONCE(n->notifier_call) == arch_timer_cpu_pm_notify; }
