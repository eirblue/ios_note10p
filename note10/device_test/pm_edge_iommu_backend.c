/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in pinned exynos-iommu.c. Registered driver inventory; no MMIO. */
#include <linux/note10_pm_edge_iommu.h>
#include <linux/cpu.h>
#include <linux/interrupt.h>
static struct n10_edge_iommu_sample n10_edge_iommu_samples[4];
static char n10_edge_iommu_names[64][64];
static unsigned int n10_edge_iommu_lengths[64];
static int n10_edge_iommu_context(void)
{
    return !irqs_disabled() && num_online_cpus() == 8 &&
           cpumask_bits(cpu_online_mask)[0] == 0xffUL;
}

static int n10_edge_iommu_visit(struct device *dev, void *context)
{
    struct n10_edge_iommu_sample *s = context;
    struct sysmmu_drvdata *data;
    unsigned long flags;
    const char *name;
    unsigned int hash = 2166136261U, i;
    int runtime_state, error = -EINVAL;
    if (s->total >= 64) return -E2BIG;
    if (!device_trylock(dev)) return -EBUSY;
    if (dev->driver != &exynos_sysmmu_driver.driver) goto unlock;
    data = dev_get_drvdata(dev);
    if (!data || data->sysmmu != dev) goto unlock;
    name = dev_name(dev);
    for (i = 0; i < 256 && name[i]; ++i) {
        unsigned char c = name[i];
        if (c < 33 || c > 126 || c == '=') goto unlock;
        hash = (hash ^ c) * 16777619U;
    }
    if (!i || i >= 64) goto unlock;
    {
        unsigned int j;
        for (j = 0; j < s->total; ++j)
            if (n10_edge_iommu_lengths[j] == i &&
                !memcmp(n10_edge_iommu_names[j], name, i)) goto unlock;
        memcpy(n10_edge_iommu_names[s->total], name, i);
        n10_edge_iommu_lengths[s->total] = i;
    }
    if ((dev->power.is_noirq_suspended && !dev->power.is_late_suspended) ||
        (dev->power.is_late_suspended && !dev->power.is_suspended) ||
        ((s->phase == 0 || s->phase == 3) &&
         (dev->power.is_late_suspended || dev->power.is_noirq_suspended))) goto unlock;
    spin_lock_irqsave(&data->lock, flags);
    if (data->activations < 0 || data->activations > 1024 ||
        data->runtime_active < 0 || data->runtime_active > 1024 ||
        data->no_rpm_control < 0 || data->no_rpm_control > SYSMMU_STATE_ENABLED) {
        spin_unlock_irqrestore(&data->lock, flags);
        goto unlock;
    }
    ++s->total;
    s->active += !!is_sysmmu_active(data);
    s->suspended += !!data->is_suspended;
    s->runtime += !!is_sysmmu_runtime_active(data);
    s->manual_off += data->no_rpm_control == SYSMMU_STATE_DISABLED;
    s->manual_on += data->no_rpm_control == SYSMMU_STATE_ENABLED;
    s->boot_hold += !!data->hold_rpm_on_boot;
    s->secure_configured += !!data->securebase;
    s->mapped += !!data->pgtable;
    s->policy_active += !!(is_sysmmu_active(data) && is_runtime_active_or_enabled(data));
    s->syscore += !!dev->power.syscore;
    s->direct += !!dev->power.direct_complete;
    s->late += !!dev->power.is_late_suspended;
    s->noirq += !!dev->power.is_noirq_suspended;
    s->prepared += !!dev->power.is_prepared;
    s->pm_suspended += !!dev->power.is_suspended;
    runtime_state = READ_ONCE(dev->power.runtime_status);
    s->runtime_other += runtime_state != RPM_ACTIVE && runtime_state != RPM_SUSPENDED;
    s->names_xor ^= hash;
    s->names_sum += hash;
    if (data->runtime_active || data->no_rpm_control || data->hold_rpm_on_boot || dev->power.syscore || dev->power.direct_complete) {
        struct n10_edge_iommu_detail *d;
        if (s->detail_count >= 8 || !i || i >= 64) {
            spin_unlock_irqrestore(&data->lock, flags);
            goto unlock;
        }
        {
            unsigned int j;
            for (j = 0; j < s->detail_count; ++j)
                if (s->details[j].length == i && !memcmp(s->details[j].name, name, i)) {
                    spin_unlock_irqrestore(&data->lock, flags);
                    goto unlock;
                }
        }
        d = &s->details[s->detail_count++];
        memcpy(d->name, name, i);
        d->length = i;
        d->activations = data->activations;
        d->runtime_count = data->runtime_active;
        d->manual = data->no_rpm_control;
        d->active = !!is_sysmmu_active(data);
        d->suspended = !!data->is_suspended;
        d->effective = !!(is_sysmmu_active(data) && is_runtime_active_or_enabled(data));
        d->syscore = !!dev->power.syscore;
        d->direct = !!dev->power.direct_complete;
        d->late = !!dev->power.is_late_suspended;
        d->noirq = !!dev->power.is_noirq_suspended;
        d->prepared = !!dev->power.is_prepared;
        d->pm_suspended = !!dev->power.is_suspended;
        d->hold = !!data->hold_rpm_on_boot;
        d->secure = !!data->securebase;
        d->mapped = !!data->pgtable;
    }
    spin_unlock_irqrestore(&data->lock, flags);
    error = 0;
unlock:
    device_unlock(dev);
    return error;
}

void n10_edge_iommu_capture(unsigned int phase, unsigned int generation)
{
    struct n10_edge_iommu_sample *s;
    if (phase >= 4) return;
    if (!phase && n10_edge_iommu_samples[0].seen && n10_edge_iommu_samples[0].generation != generation) {
        unsigned int delta = generation - n10_edge_iommu_samples[0].generation;
        if (!generation || !delta || delta >= 0x80000000U) {
            n10_edge_iommu_samples[0].error = 9; return;
        }
        memset(n10_edge_iommu_samples, 0, sizeof(n10_edge_iommu_samples));
    }
    s = &n10_edge_iommu_samples[phase];
    if (s->seen++) { s->error = 1; return; }
    s->phase = phase;
    s->generation = generation;
    if (!generation || (phase && (n10_edge_iommu_samples[phase - 1].seen != 1 ||
        n10_edge_iommu_samples[phase - 1].generation != generation ||
        n10_edge_iommu_samples[phase - 1].error))) { s->error = 2; return; }
    if (!n10_edge_iommu_context()) { s->error = 4; return; }
    memset(n10_edge_iommu_lengths, 0, sizeof(n10_edge_iommu_lengths));
    if (driver_for_each_device(&exynos_sysmmu_driver.driver, NULL, s, n10_edge_iommu_visit) || !s->total)
        s->error = 3;
    if (!n10_edge_iommu_context()) s->error = 4;
}

int n10_edge_iommu_read(struct n10_edge_iommu_sample *out, unsigned int completed)
{
    unsigned int phase, begin, next;
    if (!out || !completed) return -EINVAL;
    memcpy(out, n10_edge_iommu_samples, sizeof(n10_edge_iommu_samples));
    begin = out[0].generation;
    next = begin + 1;
    if (!next) next = 1;
    if (!begin || next != completed) return -EIO;
    for (phase = 0; phase < 4; ++phase)
        if (out[phase].seen != 1 || out[phase].error || out[phase].phase != phase ||
            out[phase].generation != begin || !out[phase].total || out[phase].total > 64 ||
            out[phase].detail_count > 8 || out[phase].detail_count > out[phase].total ||
            out[phase].active + out[phase].suspended > out[phase].total ||
            out[phase].manual_off + out[phase].manual_on > out[phase].total ||
            out[phase].policy_active > out[phase].active ||
            out[phase].policy_active > out[phase].runtime + out[phase].manual_on ||
            out[phase].syscore > out[phase].total || out[phase].direct > out[phase].total ||
            ((phase == 0 || phase == 3) && (out[phase].prepared || out[phase].pm_suspended)) ||
            out[phase].total != out[0].total || out[phase].names_xor != out[0].names_xor ||
            out[phase].names_sum != out[0].names_sum ||
            ((phase == 0 || phase == 3) && (out[phase].late || out[phase].noirq)) ||
            out[phase].noirq > out[phase].late || out[phase].late > out[phase].pm_suspended)
            return -EIO;
    return 0;
}
