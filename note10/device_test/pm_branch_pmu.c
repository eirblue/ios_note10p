/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in arm_pmu.c, called under the existing registration lock. */
#include <linux/note10_pm_branch.h>
int n10_branch_pmu(struct notifier_block *n,struct n10_branch_row *r)
{
    struct arm_pmu *p;struct pmu_hw_events *hw;unsigned int i;int count;
    if (READ_ONCE(n->notifier_call)!=cpu_pm_pmu_notify)return 0;
    p=container_of(n,struct arm_pmu,cpu_pm_nb);count=READ_ONCE(p->num_events);
    if (count<0 || count>32 || !p->hw_events)return -EINVAL;
    hw=this_cpu_ptr(p->hw_events);r->num=count;r->supported=!!cpumask_test_cpu(0,&p->supported_cpus);
    r->reset=!!READ_ONCE(p->reset);r->start=!!READ_ONCE(p->start);r->stop=!!READ_ONCE(p->stop);
    for(i=0;i<(unsigned int)count;i++) {
        struct perf_event *event=READ_ONCE(hw->events[i]);
        if(test_bit(i,hw->used_mask))r->used|=1U<<i;
        if(event)r->nonnull|=1U<<i;
        if(n10_branch_ehld_equal(event))r->match|=1U<<i;
    }
    return 1;
}
