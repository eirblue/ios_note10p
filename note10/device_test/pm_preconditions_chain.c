/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in cpu_pm.c; copy bounded fields under the registration lock. */
#include <linux/note10_pm_preconditions.h>
int n10_pre_chain(struct n10_precond_sample *out, unsigned int generation)
{
    static int (*const getters[])(struct notifier_block *, struct n10_precond_row *) = {
        n10_pre_gic, n10_pre_timer, n10_pre_fpsimd, n10_pre_sugov, n10_pre_pmu, n10_pre_ehld
    };
    struct notifier_block *n; unsigned long flags; unsigned int i;
    if (!spin_trylock_irqsave(&cpu_pm_notifier_chain.lock, flags)) return -EBUSY;
    if (!n10_pre_context(generation,1,1)) { out->error=-EIO; goto unlock; }
    n=rcu_dereference_raw(cpu_pm_notifier_chain.head);
    while (n) {
        struct n10_precond_row *r; unsigned int matches=0;
        if (out->count==N10_PRECOND_CAP) { out->error=-E2BIG; break; }
        r=&out->row[out->count++];r->priority=READ_ONCE(n->priority);
        for (i=0;i<ARRAY_SIZE(getters);i++) {
            int ret=getters[i](n,r);
            if (ret<0) { out->error=ret; goto unlock; }
            if (ret) { r->kind=i+1;matches++; }
        }
        if (matches>1) { out->error=-EIO; break; }
        n=rcu_dereference_raw(n->next);
    }
unlock:
    spin_unlock_irqrestore(&cpu_pm_notifier_chain.lock,flags);
    return out->error;
}
