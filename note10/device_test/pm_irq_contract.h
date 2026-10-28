/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_IRQ_H
#define NOTE10_PM_IRQ_H
#include <linux/types.h>
struct n10_irq_gic_sample {
    unsigned int seen, cpu, online, count, irq, preempt;
    u32 cpu_ctlr, pmr, bpr, iidr, dist_ctlr, typer;
};
struct n10_irq_arch_sample {
    unsigned int seen, cpu, online, count, irq, preempt;
    u64 daif, el, mpidr, sctlr, tcr, ttbr1, mair, cntkctl, cntfrq;
};
struct n10_pm_irq_sample {
    unsigned int generation, seen, bad, attempted, restored;
    unsigned int preempt_before, preempt_after, completed;
    unsigned long saved_flags;
    int error;
    struct n10_irq_arch_sample arch[3];
    struct n10_irq_gic_sample gic[3];
};
int n10_irq_gic_capture(unsigned int phase, struct n10_irq_gic_sample *out);
int n10_pm_irq_capture(unsigned int generation);
int n10_pm_irq_read(struct n10_pm_irq_sample *out, unsigned int completed);
#endif
