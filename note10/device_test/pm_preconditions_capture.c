/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in the existing owned CPU helper. */
#include <linux/note10_pm_preconditions.h>
static struct n10_precond_sample n10_pre_last;
static int n10_pre_bad;
/* The existing ready predicate requires IRQs on, so inspect the same protected
 * state directly when called under the CPU-PM registration lock. */
int n10_pre_context(unsigned int generation, int irq_off, unsigned int preempt)
{
    struct n10_pm_noirq_sample *s=&n10_pm_noirq_last;
    return generation && n10_pm_noirq_owned() &&
        n10_pm_active->qgeneration==generation && pm_test_level==TEST_PLATFORM &&
        !n10_pm_noirq_ops_mask() && s->seen==1 && !s->bad && !s->finished &&
        s->state==PM_SUSPEND_MEM && s->generation==generation &&
        s->late==1 && s->late_ok==1 && s->noirq==1 && s->noirq_ok==1 && s->point==1 &&
        raw_smp_processor_id()==0 && num_online_cpus()==1 && cpumask_bits(cpu_online_mask)[0]==1 &&
        !!irqs_disabled()==irq_off && preempt_count()==preempt;
}
int n10_pre_capture(unsigned int generation)
{
    struct n10_precond_sample *s=&n10_pre_last; unsigned int delta;
    if (!n10_pre_context(generation,0,0) || !preemptible()) {
        if (!n10_pre_bad) n10_pre_bad=-EPERM;return -EPERM;
    }
    if (s->seen) {
        delta=generation-s->generation;
        if (!delta || delta>=0x80000000U) { if (!n10_pre_bad)n10_pre_bad=-EIO;return -EIO; }
    }
    memset(s,0,sizeof(*s));n10_pre_bad=0;s->generation=generation;s->seen=1;
    s->error=n10_pre_chain(s,generation);s->completed=1;
    if (!n10_pre_context(generation,0,0) || !preemptible()) {
        if (!s->error)s->error=-EIO;
    }
    return s->error;
}
int n10_pre_read(struct n10_precond_sample *out, unsigned int completed)
{
    unsigned int next;int bad;
    if (!out || !completed || irqs_disabled())return -EINVAL;
    mutex_lock(&pm_mutex);memcpy(out,&n10_pre_last,sizeof(*out));bad=n10_pre_bad;mutex_unlock(&pm_mutex);
    next=out->generation+1;if (!next)next=1;
    if (bad || next!=completed || out->seen!=1 || out->completed!=1 || out->error || out->count>N10_PRECOND_CAP)return -EIO;
    return 0;
}

static struct n10_precond_gic_sample n10_pre_gic_last;
static int n10_pre_gic_bad;
int n10_pre_gic_step(unsigned int generation, unsigned int phase, u32 ctlr, u32 pmr)
{
    struct n10_precond_gic_sample *s=&n10_pre_gic_last;unsigned int delta;int ret;
    if (phase>2 || !n10_pre_context(generation,phase==1,1)) {
        if (!n10_pre_gic_bad)n10_pre_gic_bad=-EPERM;return -EPERM;
    }
    if (!phase) {
        if (s->seen) { delta=generation-s->generation; if (!delta || delta>=0x80000000U) { if(!n10_pre_gic_bad)n10_pre_gic_bad=-EIO;return -EIO; } }
        memset(s,0,sizeof(*s));n10_pre_gic_bad=0;s->generation=generation;s->seen=1;
    } else if (s->generation!=generation || s->seen!=1 || s->error || s->phase[phase-1].seen!=1 || s->phase[phase].seen) {
        if(!n10_pre_gic_bad)n10_pre_gic_bad=-EIO;return -EIO;
    }
    ret=n10_pre_gic_regs(phase,&s->phase[phase],ctlr,pmr);
    if (ret && !s->error)s->error=ret;
    if (phase==2)s->completed=1;
    return ret;
}
int n10_pre_gic_read(struct n10_precond_gic_sample *out, unsigned int completed)
{
    unsigned int next,i;int bad;
    if (!out || !completed || irqs_disabled())return -EINVAL;
    mutex_lock(&pm_mutex);memcpy(out,&n10_pre_gic_last,sizeof(*out));bad=n10_pre_gic_bad;mutex_unlock(&pm_mutex);
    next=out->generation+1;if(!next)next=1;
    if (bad || next!=completed || out->seen!=1 || out->completed!=1 || out->error)return -EIO;
    for(i=0;i<3;i++)if(out->phase[i].seen!=1)return -EIO;
    return 0;
}
