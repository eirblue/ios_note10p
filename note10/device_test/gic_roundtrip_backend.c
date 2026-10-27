/* SPDX-License-Identifier: GPL-2.0-only */
/* Included only in the pinned GICv2 MMIO driver. Distributor reads only.
 * Never acknowledge an interrupt or change control, enable, routing or BPR.
 */
#include <linux/cpu.h>
#include <linux/irqflags.h>
#include <linux/smp.h>
#include <linux/note10_gic_roundtrip.h>

static void n10_gic_sample_cpu(void *argument)
{
    struct n10_gic_sample *samples = argument, *sample;
    unsigned int cpu = smp_processor_id();
    void __iomem *base, *dist;
    unsigned long flags;
    if (cpu >= 8) return;
    sample = &samples[cpu];
    if (sample->seen++) { sample->status = 1; return; }
    base = gic_data_cpu_base(&gic_data[0]);
    dist = gic_data_dist_base(&gic_data[0]);
    if (!base || !dist) { sample->status = 2; return; }
    sample->irq_before = irqs_disabled() ? 1 : 0;
    local_irq_save(flags);
    sample->ctlr = readl_relaxed(base + GIC_CPU_CTRL);
    sample->pmr = readl_relaxed(base + GIC_CPU_PRIMASK);
    sample->bpr = readl_relaxed(base + GIC_CPU_BINPOINT);
    sample->iidr = readl_relaxed(base + GIC_CPU_IDENT);
    sample->dist_ctlr = readl_relaxed(dist + GIC_DIST_CTRL);
    sample->typer = readl_relaxed(dist + GIC_DIST_CTR);
    if (!(sample->ctlr & 1) || !(sample->dist_ctlr & 3) ||
        !sample->pmr || sample->pmr > 255) {
        sample->status = 3;
        goto irq_restore;
    }
    writel_relaxed(0, base + GIC_CPU_PRIMASK);
    dsb(sy);
    isb();
    sample->masked = readl_relaxed(base + GIC_CPU_PRIMASK);
    /* Every path after the first PMR write restores the original PMR. */
    writel_relaxed(sample->pmr, base + GIC_CPU_PRIMASK);
    dsb(sy);
    isb();
    sample->restored = readl_relaxed(base + GIC_CPU_PRIMASK);
    sample->ctlr_after = readl_relaxed(base + GIC_CPU_CTRL);
    sample->bpr_after = readl_relaxed(base + GIC_CPU_BINPOINT);
    if (sample->masked) sample->status = 4;
    if (sample->restored != sample->pmr || sample->ctlr_after != sample->ctlr ||
        sample->bpr_after != sample->bpr) sample->status = 5;
irq_restore:
    local_irq_restore(flags);
    sample->irq_after = irqs_disabled() ? 1 : 0;
    if (sample->irq_after != sample->irq_before) sample->status = 6;
}

int n10_gic_roundtrip(struct n10_gic_sample *samples, unsigned int count)
{
    unsigned int cpu;
    int ret = 0;
    if (!samples || count != 8 || !gic_data[0].domain) return -EINVAL;
    memset(samples, 0, sizeof(*samples) * count);
    cpus_read_lock();
    if (num_online_cpus() != 8) { ret = -EBUSY; goto out; }
    for_each_online_cpu(cpu)
        if (cpu >= 8) { ret = -EOPNOTSUPP; goto out; }
    on_each_cpu(n10_gic_sample_cpu, samples, 1);
    for (cpu = 0; cpu < 8; ++cpu)
        if (samples[cpu].seen != 1 || samples[cpu].status) ret = -EIO;
out:
    cpus_read_unlock();
    return ret;
}
