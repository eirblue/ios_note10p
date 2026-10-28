/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in pinned device PM core. Framework flags, not DMA idleness. */
#include <linux/note10_pm_edge_dma.h>
#include <linux/note10_pm_edge_iommu.h>
#include <linux/note10_pm_edge_syscore.h>
#include <linux/cpu.h>
#include <linux/interrupt.h>
static struct n10_edge_dma_sample n10_edge_dma_samples[4];
static int n10_edge_dma_context(void)
{
    return !irqs_disabled() && num_online_cpus() == 8 &&
           cpumask_bits(cpu_online_mask)[0] == 0xffUL;
}
void n10_edge_dma_capture(unsigned int phase, unsigned int generation)
{
    struct list_head *heads[] = { &dpm_list, &dpm_prepared_list,
        &dpm_suspended_list, &dpm_late_early_list, &dpm_noirq_list };
    struct n10_edge_dma_sample *s;
    struct list_head *entry;
    unsigned int h;
    if (phase >= 4) return;
    if (!phase && n10_edge_dma_samples[0].seen && n10_edge_dma_samples[0].generation != generation) {
        unsigned int delta = generation - n10_edge_dma_samples[0].generation;
        if (!generation || !delta || delta >= 0x80000000U) {
            n10_edge_dma_samples[0].error = 9; return;
        }
        memset(n10_edge_dma_samples, 0, sizeof(n10_edge_dma_samples));
    }
    s = &n10_edge_dma_samples[phase];
    if (s->seen++) { s->error = 1; return; }
    s->phase = phase; s->generation = generation;
    if (!generation || (phase && (n10_edge_dma_samples[phase-1].seen != 1 ||
        n10_edge_dma_samples[phase-1].generation != generation ||
        n10_edge_dma_samples[phase-1].error))) { s->error = 2; return; }
    if (!n10_edge_dma_context()) { s->error = 3; return; }
    if (!mutex_trylock(&dpm_list_mtx)) { s->error = 4; return; }
    for (h = 0; h < ARRAY_SIZE(heads); ++h) {
        list_for_each(entry, heads[h]) {
            struct device *dev;
            const char *name;
            unsigned int i, hash = 2166136261U, covered;
            int runtime;
            if (s->total == 4096) { s->error = 5; goto out; }
            ++s->total; dev = to_device(entry);
            if (!READ_ONCE(dev->dma_mask) && !READ_ONCE(dev->coherent_dma_mask)) continue;
            ++s->dma; name = dev_name(dev);
            for (i = 0; i < 256 && name[i]; ++i)
                hash = (hash ^ (unsigned char)name[i]) * 16777619U;
            if (!i || i == 256) { s->error = 6; goto out; }
            s->names_xor ^= hash; s->names_sum += hash;
            s->prepared += !!dev->power.is_prepared;
            s->suspended += !!dev->power.is_suspended;
            s->late += !!dev->power.is_late_suspended;
            s->noirq += !!dev->power.is_noirq_suspended;
            s->direct += !!dev->power.direct_complete;
            s->syscore += !!dev->power.syscore;
            covered = phase == 1 ? dev->power.is_late_suspended :
                      phase == 2 ? dev->power.is_noirq_suspended : 0;
            if (covered) ++s->covered;
            else if (dev->power.direct_complete) ++s->exception_direct;
            else if (dev->power.syscore) ++s->exception_syscore;
            else ++s->uncovered;
            runtime = READ_ONCE(dev->power.runtime_status);
            if (runtime == RPM_ACTIVE) ++s->active;
            else if (runtime == RPM_SUSPENDED) ++s->runtime_suspended;
            else ++s->runtime_other;
            if ((dev->power.is_noirq_suspended && !dev->power.is_late_suspended) ||
                (dev->power.is_late_suspended && !dev->power.is_suspended) ||
                ((phase == 0 || phase == 3) &&
                 (dev->power.is_late_suspended || dev->power.is_noirq_suspended))) {
                s->error = 7; goto out;
            }
        }
    }
out:
    mutex_unlock(&dpm_list_mtx);
    if (!n10_edge_dma_context()) s->error = 8;
}
int n10_edge_dma_read(struct n10_edge_dma_sample *out, unsigned int completed)
{
    unsigned int phase, next;
    if (!out || !completed) return -EINVAL;
    memcpy(out, n10_edge_dma_samples, sizeof(n10_edge_dma_samples));
    next = out[0].generation + 1; if (!next) next = 1;
    if (!out[0].generation || next != completed) return -EIO;
    for (phase = 0; phase < 4; ++phase) {
        struct n10_edge_dma_sample *s = &out[phase];
        if (s->seen != 1 || s->error || s->phase != phase ||
            s->generation != out[0].generation || s->dma > s->total ||
            s->covered + s->exception_direct + s->exception_syscore + s->uncovered != s->dma ||
            s->active + s->runtime_suspended + s->runtime_other != s->dma ||
            !s->dma || s->prepared > s->dma || s->suspended > s->dma ||
            s->late > s->suspended || s->noirq > s->late ||
            s->direct > s->dma || s->syscore > s->dma ||
            s->exception_direct > s->direct || s->exception_syscore > s->syscore ||
            s->covered != (phase == 1 ? s->late : phase == 2 ? s->noirq : 0) ||
            ((phase == 0 || phase == 3) && (s->prepared || s->suspended || s->late || s->noirq)) ||
            s->total != out[0].total || s->dma != out[0].dma ||
            s->names_xor != out[0].names_xor || s->names_sum != out[0].names_sum)
            return -EIO;
    }
    return 0;
}

void n10_edge_capture(unsigned int phase, unsigned int generation)
{
    n10_edge_dma_capture(phase, generation);
    n10_edge_iommu_capture(phase, generation);
    if (phase == 0 || phase == 3) n10_edge_syscore_capture(phase, generation);
}
