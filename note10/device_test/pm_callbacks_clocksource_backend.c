/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in kernel/time/clocksource.c. */
#include <linux/note10_pm_callbacks.h>
int n10_cb_clocksource(struct n10_cb_family *out)
{
    struct clocksource *cs;
    unsigned int current_count = 0;
    if (!mutex_trylock(&clocksource_mutex)) return -EBUSY;
    list_for_each_entry(cs, &clocksource_list, list) {
        struct n10_cb_entry *e;
        if (out->count == 32) { out->error = -E2BIG; break; }
        e = &out->entry[out->count++];
        if (n10_cb_name(e->name, READ_ONCE(cs->name))) { out->error = -EINVAL; break; }
        e->a = cs == curr_clocksource; current_count += e->a;
        e->callback[0] = (unsigned long)READ_ONCE(cs->suspend);
        e->callback[1] = (unsigned long)READ_ONCE(cs->resume);
    }
    if (!out->error && (!out->count || current_count != 1)) out->error = -EINVAL;
    mutex_unlock(&clocksource_mutex);
    return out->error;
}
