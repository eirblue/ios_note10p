/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in the owned PM CPU helper; no print, allocation, timer or callbacks. */
#include <linux/note10_pm_irq.h>
#include <linux/preempt.h>
#include <linux/irqflags.h>
#include <asm/sysreg.h>
#include <asm/ptrace.h>
static struct n10_pm_irq_sample n10_pm_irq_last;
static void n10_pm_irq_error(struct n10_pm_irq_sample *s, int error)
{
    if (!s->error && error) s->error=error;
}
static int n10_pm_irq_arch(unsigned int phase, struct n10_irq_arch_sample *s)
{
    if (s->seen++) return -EIO;
    s->cpu=raw_smp_processor_id();s->online=(unsigned int)cpumask_bits(cpu_online_mask)[0];
    s->count=num_online_cpus();s->irq=!!irqs_disabled();s->preempt=preempt_count();
    if (s->cpu || s->online!=1 || s->count!=1 || s->preempt!=1 || s->irq!=(phase==1)) return -EIO;
    s->daif=read_sysreg(daif);s->el=read_sysreg(CurrentEL);s->mpidr=read_sysreg(mpidr_el1);
    s->sctlr=read_sysreg(sctlr_el1);s->tcr=read_sysreg(tcr_el1);s->ttbr1=read_sysreg(ttbr1_el1);
    s->mair=read_sysreg(mair_el1);s->cntkctl=read_sysreg(cntkctl_el1);s->cntfrq=read_sysreg(cntfrq_el0);
    if (s->el!=4 || (s->sctlr & 0x1005)!=0x1005 || s->cntfrq!=26000000 ||
        !!(s->daif & PSR_I_BIT)!=(phase==1)) return -EIO;
    return 0;
}
int n10_pm_irq_capture(unsigned int generation)
{
    struct n10_pm_irq_sample *s=&n10_pm_irq_last;
    unsigned int i;
    int error;
    /* Do not erase an earlier record for an invalid or foreign attempt. */
    if (!generation || !n10_pm_noirq_ready(PM_SUSPEND_MEM) ||
        generation!=n10_pm_active->qgeneration || !preemptible() ||
        raw_smp_processor_id()!=0 || num_online_cpus()!=1 || cpumask_bits(cpu_online_mask)[0]!=1) {
        if (s->seen) s->bad=1;
        else { s->seen=1;s->generation=generation;s->error=-EPERM; }
        return -EPERM;
    }
    if (s->seen && s->generation!=generation) {
        unsigned int delta=generation-s->generation;
        if (!delta || delta>=0x80000000U) { s->bad=1;return -EIO; }
        memset(s,0,sizeof(*s));
    }
    if (s->seen++) { s->bad=1;return -EIO; }
    s->generation=generation;s->preempt_before=preempt_count();
    preempt_disable();
    error=n10_pm_irq_arch(0,&s->arch[0]);n10_pm_irq_error(s,error);
    if (!error) { error=n10_irq_gic_capture(0,&s->gic[0]);n10_pm_irq_error(s,error); }
    if (s->error) goto preempt_restore;
    s->attempted=1;
    local_irq_save(s->saved_flags);
    error=n10_pm_irq_arch(1,&s->arch[1]);n10_pm_irq_error(s,error);
    if (!error) { error=n10_irq_gic_capture(1,&s->gic[1]);n10_pm_irq_error(s,error); }
    local_irq_restore(s->saved_flags);s->restored=1;
    error=n10_pm_irq_arch(2,&s->arch[2]);n10_pm_irq_error(s,error);
    if (!error) { error=n10_irq_gic_capture(2,&s->gic[2]);n10_pm_irq_error(s,error); }
    if (s->saved_flags!=s->arch[0].daif || s->arch[1].daif!=(s->arch[0].daif|PSR_I_BIT) ||
        s->arch[2].daif!=s->arch[0].daif) n10_pm_irq_error(s,-EIO);
    for (i=1;i<3;++i) {
        struct n10_irq_arch_sample *a=&s->arch[0],*b=&s->arch[i];
        struct n10_irq_gic_sample *x=&s->gic[0],*y=&s->gic[i];
        if (a->el!=b->el || a->mpidr!=b->mpidr || a->sctlr!=b->sctlr || a->tcr!=b->tcr ||
            a->ttbr1!=b->ttbr1 || a->mair!=b->mair || a->cntkctl!=b->cntkctl || a->cntfrq!=b->cntfrq ||
            x->cpu_ctlr!=y->cpu_ctlr || x->pmr!=y->pmr || x->bpr!=y->bpr || x->iidr!=y->iidr ||
            x->dist_ctlr!=y->dist_ctlr || x->typer!=y->typer) n10_pm_irq_error(s,-EIO);
    }
preempt_restore:
    preempt_enable();s->preempt_after=preempt_count();s->completed=1;
    if (s->preempt_after!=s->preempt_before || irqs_disabled() || raw_smp_processor_id()!=0 ||
        num_online_cpus()!=1 || cpumask_bits(cpu_online_mask)[0]!=1) n10_pm_irq_error(s,-EIO);
    return s->error;
}
int n10_pm_irq_read(struct n10_pm_irq_sample *out, unsigned int completed)
{
    unsigned int next,phase;
    if (!out || !completed || irqs_disabled()) return -EINVAL;
    mutex_lock(&pm_mutex);memcpy(out,&n10_pm_irq_last,sizeof(*out));mutex_unlock(&pm_mutex);
    next=out->generation+1;if (!next) next=1;
    if (!out->generation || next!=completed || out->seen!=1 || out->bad || out->error ||
        out->attempted!=1 || out->restored!=1 || out->completed!=1 ||
        out->preempt_before || out->preempt_after) return -EIO;
    for (phase=0;phase<3;++phase)
        if (out->arch[phase].seen!=1 || out->gic[phase].seen!=1) return -EIO;
    return 0;
}
