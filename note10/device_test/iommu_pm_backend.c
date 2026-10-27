/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in pinned exynos-iommu.c. Registered driver inventory; no MMIO. */
#include <linux/note10_iommu_pm.h>
static struct n10_iommu_pm_sample n10_iommu_samples[3];

static int n10_iommu_visit(struct device *dev, void *context)
{
    struct n10_iommu_pm_sample *s = context;
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
    for (i = 0; i < 256 && name[i]; ++i)
        hash = (hash ^ (unsigned char)name[i]) * 16777619U;
    if (i == 256) goto unlock;
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
    s->prepared += !!dev->power.is_prepared;
    s->pm_suspended += !!dev->power.is_suspended;
    runtime_state = READ_ONCE(dev->power.runtime_status);
    s->runtime_other += runtime_state != RPM_ACTIVE && runtime_state != RPM_SUSPENDED;
    s->names_xor ^= hash;
    s->names_sum += hash;
    if (data->runtime_active || data->no_rpm_control || data->hold_rpm_on_boot || dev->power.syscore) {
        struct n10_iommu_pm_detail *d;
        if (s->detail_count >= 8 || !i || i >= 64) {
            spin_unlock_irqrestore(&data->lock, flags);
            goto unlock;
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

void n10_iommu_pm_capture(unsigned int phase, unsigned int generation)
{
    struct n10_iommu_pm_sample *s;
    if (phase >= 3) return;
    if (!phase && (!n10_iommu_samples[0].seen || n10_iommu_samples[0].generation != generation))
        memset(n10_iommu_samples, 0, sizeof(n10_iommu_samples));
    s = &n10_iommu_samples[phase];
    if (s->seen++) { s->error = 1; return; }
    s->phase = phase;
    s->generation = generation;
    if (!generation || (phase && (n10_iommu_samples[phase - 1].seen != 1 ||
        n10_iommu_samples[phase - 1].generation != generation))) { s->error = 2; return; }
    if (driver_for_each_device(&exynos_sysmmu_driver.driver, NULL, s, n10_iommu_visit) || !s->total)
        s->error = 3;
}

int n10_iommu_pm_read(struct n10_iommu_pm_sample *out, unsigned int completed)
{
    unsigned int phase, begin, next;
    if (!out || !completed) return -EINVAL;
    memcpy(out, n10_iommu_samples, sizeof(n10_iommu_samples));
    begin = out[0].generation;
    next = begin + 1;
    if (!next) next = 1;
    if (!begin || next != completed) return -EIO;
    for (phase = 0; phase < 3; ++phase)
        if (out[phase].seen != 1 || out[phase].error || out[phase].phase != phase ||
            out[phase].generation != begin) return -EIO;
    return 0;
}
