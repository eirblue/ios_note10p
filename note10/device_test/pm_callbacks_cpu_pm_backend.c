/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in kernel/cpu_pm.c; membership only, never call notifiers. */
#include <linux/note10_pm_callbacks.h>
int n10_cb_cpu_pm(struct n10_cb_family *out)
{
    struct notifier_block *n;
    unsigned long flags;
    if (!spin_trylock_irqsave(&cpu_pm_notifier_chain.lock, flags)) return -EBUSY;
    n = rcu_dereference_raw(cpu_pm_notifier_chain.head);
    while (n) {
        struct n10_cb_entry *e;
        if (out->count == 32) { out->error = -E2BIG; break; }
        e = &out->entry[out->count++];
        e->priority = READ_ONCE(n->priority);
        e->callback[0] = (unsigned long)READ_ONCE(n->notifier_call);
        n = rcu_dereference_raw(n->next);
    }
    spin_unlock_irqrestore(&cpu_pm_notifier_chain.lock, flags);
    return out->error;
}

