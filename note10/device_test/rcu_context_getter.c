/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in pinned tree.c. Local RAM observations only; no RCU transition. */
#include <linux/note10_pm_preconditions.h>
#include <linux/note10_rcu_context_audit.h>
int n10_rcu_get(struct n10_rcu_row *row, unsigned int generation)
{
    struct rcu_dynticks *rdtp; long long nesting; int dynticks, nmi, task_nesting; u32 special; bool disabled;
    if (!row || !n10_pre_context(generation, 1, 1) || in_interrupt()) return -EPERM;
    rdtp = this_cpu_ptr(&rcu_dynticks);
    dynticks = atomic_read(&rdtp->dynticks);
    nesting = READ_ONCE(rdtp->dynticks_nesting);
    nmi = READ_ONCE(rdtp->dynticks_nmi_nesting);
    task_nesting = READ_ONCE(current->rcu_read_lock_nesting);
    special = READ_ONCE(current->rcu_read_unlock_special.s);
    disabled = __this_cpu_read(disable_rcu_irq_enter);
    row->watching = !!(dynticks & RCU_DYNTICK_CTRL_CTR);
    row->nesting_class = nesting < 0 ? 0 : nesting == 0 ? 1 : 2;
    row->positive_headroom_two = nesting > 0 && nesting <= LLONG_MAX - 2;
    row->nmi_nonzero = !!nmi; row->task_nesting_nonzero = !!task_nesting;
    row->task_special_nonzero = !!special; row->irq_enter_disabled = !!disabled;
    return 0;
}
