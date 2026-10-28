/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in arm_pmu.c; chain membership protects enclosing PMU lifetime. */
#include <linux/note10_pm_preconditions.h>
int n10_pre_pmu(struct notifier_block *n, struct n10_precond_row *r)
{
    struct arm_pmu *pmu; struct pmu_hw_events *hw; unsigned int i, count=0, used=0; u32 mask=0; int num;
    if (READ_ONCE(n->notifier_call) != cpu_pm_pmu_notify) return 0;
    pmu=container_of(n,struct arm_pmu,cpu_pm_nb);num=READ_ONCE(pmu->num_events);
    if (num<0 || num>32 || !pmu->hw_events) return -EINVAL;
    hw=this_cpu_ptr(pmu->hw_events);
    for (i=0;i<(unsigned int)num;i++) { if (test_bit(i,hw->used_mask)) { mask|=1U<<i;used++; } if (READ_ONCE(hw->events[i])) count++; }
    r->valid=31;r->value[0]=!!cpumask_test_cpu(0,&pmu->supported_cpus);r->value[1]=num;r->value[2]=mask;r->value[3]=used;r->value[4]=count;
    return 1;
}
