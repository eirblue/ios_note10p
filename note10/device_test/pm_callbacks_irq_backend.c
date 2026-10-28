/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in kernel/irq/generic-chip.c; eligibility remains unknown. */
#include <linux/note10_pm_callbacks.h>
int n10_cb_irq(struct n10_cb_family *out)
{
    struct irq_chip_generic *gc;
    unsigned long flags;
    if (!raw_spin_trylock_irqsave(&gc_lock, flags)) return -EBUSY;
    list_for_each_entry(gc, &gc_list, list) {
        struct n10_cb_entry *e;
        if (out->count == 64) { out->error = -E2BIG; break; }
        e = &out->entry[out->count++];
        e->a = READ_ONCE(gc->irq_base); e->b = READ_ONCE(gc->num_ct);
        e->c = READ_ONCE(gc->irq_cnt); e->mask = READ_ONCE(gc->installed);
        e->d = !!READ_ONCE(gc->domain);
        e->callback[0] = (unsigned long)READ_ONCE(gc->suspend);
        e->callback[1] = (unsigned long)READ_ONCE(gc->resume);
        if (e->b) {
            e->callback[2] = (unsigned long)READ_ONCE(gc->chip_types[0].chip.irq_suspend);
            e->callback[3] = (unsigned long)READ_ONCE(gc->chip_types[0].chip.irq_resume);
            e->callback[4] = (unsigned long)READ_ONCE(gc->chip_types[0].chip.irq_pm_shutdown);
        }
    }
    raw_spin_unlock_irqrestore(&gc_lock, flags);
    return out->error;
}
