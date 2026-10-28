/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in kernel/time/clockevents.c; remote state is not frozen. */
#include <linux/note10_pm_callbacks.h>
int n10_cb_clockevent(struct n10_cb_family *out)
{
    struct clock_event_device *ce;
    unsigned long flags;
    if (!raw_spin_trylock_irqsave(&clockevents_lock, flags)) return -EBUSY;
    list_for_each_entry(ce, &clockevent_devices, list) {
        struct n10_cb_entry *e;
        const struct cpumask *mask;
        if (out->count == 64) { out->error = -E2BIG; break; }
        e = &out->entry[out->count++];
        if (n10_cb_name(e->name, READ_ONCE(ce->name))) { out->error = -EINVAL; break; }
        e->a = READ_ONCE(ce->state_use_accessors); e->b = READ_ONCE(ce->features);
        e->x = READ_ONCE(ce->bound_on); e->y = READ_ONCE(ce->irq);
        mask = READ_ONCE(ce->cpumask);
        if (!mask) { out->error = -EINVAL; break; }
        e->mask = READ_ONCE(cpumask_bits(mask)[0]);
        e->callback[0] = (unsigned long)READ_ONCE(ce->suspend);
        e->callback[1] = (unsigned long)READ_ONCE(ce->resume);
    }
    if (!out->error && !out->count) out->error = -EINVAL;
    raw_spin_unlock_irqrestore(&clockevents_lock, flags);
    return out->error;
}
