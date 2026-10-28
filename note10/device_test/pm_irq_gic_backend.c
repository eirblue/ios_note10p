/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in the pinned GICv2 driver. Six fixed non-secure reads; no writes. */
#include <linux/note10_pm_irq.h>
#include <linux/cpu.h>
#include <linux/preempt.h>
#include <linux/irqflags.h>
int n10_irq_gic_capture(unsigned int phase, struct n10_irq_gic_sample *out)
{
    void __iomem *cpu, *dist;
    if (!out || phase > 2) return -EINVAL;
    if (out->seen++) return -EIO;
    out->cpu=raw_smp_processor_id();
    out->online=(unsigned int)cpumask_bits(cpu_online_mask)[0];
    out->count=num_online_cpus();out->irq=!!irqs_disabled();out->preempt=preempt_count();
    if (out->cpu || out->online!=1 || out->count!=1 || out->preempt!=1 ||
        out->irq!=(phase==1) || !gic_data[0].domain) return -EIO;
    cpu=gic_data_cpu_base(&gic_data[0]);dist=gic_data_dist_base(&gic_data[0]);
    if (!cpu || !dist) return -ENODEV;
    out->cpu_ctlr=readl_relaxed(cpu+GIC_CPU_CTRL);
    out->pmr=readl_relaxed(cpu+GIC_CPU_PRIMASK);
    out->bpr=readl_relaxed(cpu+GIC_CPU_BINPOINT);
    out->iidr=readl_relaxed(cpu+GIC_CPU_IDENT);
    out->dist_ctlr=readl_relaxed(dist+GIC_DIST_CTRL);
    out->typer=readl_relaxed(dist+GIC_DIST_CTR);
    if (!(out->cpu_ctlr & 1) || !(out->dist_ctlr & 3) || !out->pmr || out->pmr>255)
        return -EIO;
    return 0;
}
