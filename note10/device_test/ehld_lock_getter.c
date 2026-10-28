/* SPDX-License-Identifier: GPL-2.0-only */
/* Included from pinned exynos-ehld.c: only the owned ctrl lock/running field. */
#include <linux/note10_pm_preconditions.h>
#include <linux/note10_ehld_lock_audit.h>
#include <linux/kernel.h>
#include <linux/spinlock.h>
int n10_ehld_lock_get(struct n10_ehld_lock_row *row,
		      struct notifier_block *n,
		      const struct n10_precond_sample *pre,
		      unsigned int index, unsigned int generation)
{
	struct exynos_ehld_ctrl *ctrl;
	const struct n10_precond_row *old;
	int running;

	if (!row || !pre || !n || !generation || !n10_pre_context(generation, 1, 1) ||
	    in_interrupt() || index >= pre->count || pre->count > N10_PRECOND_CAP ||
	    pre->generation != generation || pre->seen != 1 || pre->bad ||
	    pre->completed || pre->error)
		return -EPERM;
	old = &pre->row[index];
	if (n != &exynos_ehld_c2_pm_nb ||
	    READ_ONCE(n->notifier_call) != exynos_ehld_c2_pm_notifier ||
	    old->kind != N10_PRE_EHLD || old->valid != 3 ||
	    old->value[0] < INT_MIN || old->value[0] > INT_MAX ||
	    row->index != index)
		return -EIO;
	/* Static per-CPU ctrl lifetime; all identity checks precede this pointer. */
	ctrl = this_cpu_ptr(&ehld_ctrl);
	if (!raw_spin_trylock(&ctrl->lock)) {
		if (!n10_pre_context(generation, 1, 1) || in_interrupt())
			return -EPERM;
		row->lock_available = 0;
		row->running_valid = 0;
		row->running = 0;
		return 0;
	}
	if (!n10_pre_context(generation, 1, 2) || in_interrupt()) {
		raw_spin_unlock(&ctrl->lock);
		return -EPERM;
	}
	running = READ_ONCE(ctrl->ehld_running);
	if (!!running != !!old->value[0]) {
		raw_spin_unlock(&ctrl->lock);
		return -EIO;
	}
	row->lock_available = 1;
	row->running_valid = 1;
	row->running = !!running;
	raw_spin_unlock(&ctrl->lock);
	if (!n10_pre_context(generation, 1, 1) || in_interrupt())
		return -EPERM;
	return 0;
}
