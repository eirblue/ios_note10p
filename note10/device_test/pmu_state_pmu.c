/* SPDX-License-Identifier: GPL-2.0-only */
/* Ordinary affected-CPU perf serialization supplies event lifetime. The chain
 * lock protects notifier and PMU membership only; it is not an event lock. */
#include <linux/note10_pmu_state_audit.h>
#include <linux/note10_pm_preconditions.h>
int n10_state_pmu(struct notifier_block *n,struct n10_state_row *r,unsigned int generation)
{
    struct arm_pmu *p; struct pmu_hw_events *hw; unsigned int i; int count;
    if (!n10_pre_context(generation,1,1) || in_interrupt()) return -EPERM;
    if (READ_ONCE(n->notifier_call)!=cpu_pm_pmu_notify) return 0;
    p=container_of(n,struct arm_pmu,cpu_pm_nb);
    count=READ_ONCE(p->num_events);
    if (count<0 || count>32 || !p->hw_events) return -EINVAL;
    r->num=count;r->supported=!!cpumask_test_cpu(0,&p->supported_cpus);
    if (!r->supported) return -ENODEV;
    hw=this_cpu_ptr(p->hw_events);
    for (i=0;i<(unsigned int)count;i++) {
        struct perf_event *event; u32 bit=1U<<i; int idx,state,affinity,oncpu,generic;
        if (!test_bit(i,hw->used_mask)) continue;
        r->used|=bit;event=READ_ONCE(hw->events[i]);
        if (!event) return -EIO;
        r->present|=bit;
        if (READ_ONCE(event->pmu)!=&p->pmu) return -EXDEV;
        r->owned|=bit;idx=READ_ONCE(event->hw.idx);
        if (idx!=(int)i) return -EIO;
        r->observed|=bit;state=READ_ONCE(event->hw.state);
        affinity=READ_ONCE(event->cpu);oncpu=READ_ONCE(event->oncpu);
        generic=READ_ONCE(event->state);
        if (state==0) r->running|=bit;
        if (state & PERF_HES_STOPPED) r->stopped|=bit;
        if (state & PERF_HES_UPTODATE) r->uptodate|=bit;
        if ((state & ~(PERF_HES_STOPPED|PERF_HES_UPTODATE)) || state==PERF_HES_UPTODATE) r->abnormal|=bit;
        if (affinity==0) r->affinity0|=bit;
        else if (affinity==-1) r->unbound|=bit;
        else r->other|=bit;
        if (oncpu==0) r->oncpu0|=bit;
        if (generic==PERF_EVENT_STATE_ACTIVE) r->active|=bit;
    }
    return 1;
}
