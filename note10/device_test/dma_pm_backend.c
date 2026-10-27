/* SPDX-License-Identifier: GPL-2.0-only */
/* Included only in pinned drivers/base/power/main.c. No device/MMIO writes.
 * Do not take device_lock while holding dpm_list_mtx. PM flag reads are a
 * framework snapshot after async callbacks have completed, not DMA state.
 */
#include <linux/note10_dma_pm.h>
static struct n10_dma_pm_sample n10_dma_pm_samples[3];

static unsigned int n10_dma_name_hash(const char *name)
{
    unsigned int hash = 2166136261U, i;
    for (i = 0; i < 256 && name[i]; ++i)
        hash = (hash ^ (unsigned char)name[i]) * 16777619U;
    return hash;
}

void n10_dma_pm_capture(unsigned int phase, unsigned int generation)
{
    struct list_head *heads[] = { &dpm_list, &dpm_prepared_list,
        &dpm_suspended_list, &dpm_late_early_list, &dpm_noirq_list };
    struct n10_dma_pm_sample *s;
    struct list_head *entry;
    unsigned int i, hash;
    if (phase >= 3) return;
    if (phase == 0 && (!n10_dma_pm_samples[0].seen ||
        n10_dma_pm_samples[0].generation != generation))
        memset(n10_dma_pm_samples, 0, sizeof(n10_dma_pm_samples));
    s = &n10_dma_pm_samples[phase];
    if (s->seen++) { s->error = 1; return; }
    s->phase = phase;
    s->generation = generation;
    if (!generation || (phase && (n10_dma_pm_samples[phase - 1].seen != 1 ||
        n10_dma_pm_samples[phase - 1].generation != generation))) {
        s->error = 2;
        return;
    }
    mutex_lock(&dpm_list_mtx);
    for (i = 0; i < ARRAY_SIZE(heads); ++i) {
        list_for_each(entry, heads[i]) {
            struct device *dev;
            int runtime;
            if (s->total == 4096) { s->error = 3; goto out; }
            ++s->total;
            dev = to_device(entry);
            if (!READ_ONCE(dev->dma_mask) && !READ_ONCE(dev->coherent_dma_mask)) continue;
            ++s->dma;
            hash = n10_dma_name_hash(dev_name(dev));
            s->names_xor ^= hash;
            s->names_sum += hash;
            /* Exclusive categories: flags do not prove that hardware is idle. */
            if (dev->power.is_suspended) ++s->suspended;
            else if (dev->power.direct_complete) ++s->direct;
            else if (dev->power.syscore) ++s->syscore;
            else ++s->uncovered;
            if (dev->power.is_prepared) ++s->prepared;
            runtime = READ_ONCE(dev->power.runtime_status);
            if (runtime == RPM_ACTIVE) ++s->runtime_active;
            else if (runtime == RPM_SUSPENDED) ++s->runtime_suspended;
            else ++s->runtime_other;
        }
    }
out:
    mutex_unlock(&dpm_list_mtx);
}

int n10_dma_pm_read(struct n10_dma_pm_sample *out, unsigned int generation)
{
    unsigned int phase;
    if (!out || !generation) return -EINVAL;
    memcpy(out, n10_dma_pm_samples, sizeof(n10_dma_pm_samples));
    for (phase = 0; phase < 3; ++phase)
        if (out[phase].seen != 1 || out[phase].error ||
            out[phase].phase != phase || out[phase].generation != generation) return -EIO;
    return 0;
}
