/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in pinned abox_qos.c. No PM, QoS update, flush or MMIO request. */
#include <linux/note10_abox_pm.h>
void n10_abox_qos_capture(struct device *dev, struct n10_abox_pm_sample *s)
{
    unsigned int ids[64], values[64], i, j, maximum = 0;
    unsigned long flags;
    bool ended = false;
    s->qos_seen = 1; s->qos_error = 1;
    if (dev != READ_ONCE(dev_abox)) return;
    spin_lock_irqsave(&abox_qos_lock, flags);
    s->qos_applied = READ_ONCE(abox_qos_aud.val);
    s->qos_target = abox_qos_target(&abox_qos_aud);
    for (i = 0; i < 64; ++i) {
        ids[i] = abox_qos_aud.req_array[i].id;
        values[i] = abox_qos_aud.req_array[i].val;
    }
    spin_unlock_irqrestore(&abox_qos_lock, flags);
    s->qos_work_pending = !!work_pending(&abox_qos_work);
    s->qos_error = 2;
    for (i = 0; i < 64; ++i) {
        if (!ids[i]) { ended = true; continue; }
        if (ended) return;
        for (j = 0; j < i; ++j) if (ids[j] == ids[i]) return;
        ++s->qos_registered;
        if (values[i]) {
            if (!s->qos_active) { s->qos_first_id = ids[i]; s->qos_first_value = values[i]; }
            ++s->qos_active;
        }
        if (ids[i] == ABOX_CPU_GEAR_ABSOLUTE) s->qos_absolute = values[i];
        if (ids[i] == DEFAULT_CPU_GEAR_ID) s->qos_default = values[i];
        if (maximum < values[i]) maximum = values[i];
    }
    if (maximum != s->qos_target) return;
    s->qos_error = 0;
}
