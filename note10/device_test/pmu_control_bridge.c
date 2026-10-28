/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in arm_pmu.c. The notifier lock protects PMU membership, not perf events. */
#include <linux/note10_pmu_control_audit.h>
#include <linux/note10_pm_preconditions.h>
int n10_ctl_consider(struct notifier_block *n,struct n10_ctl_stage *s,unsigned int index,unsigned int generation)
{
    if (!s || !n || !n10_pre_context(generation,1,1) || in_interrupt()) return -EPERM;
    if (READ_ONCE(n->notifier_call)!=cpu_pm_pmu_notify) return 0;
    if (s->count>=32) return -E2BIG;
    s->count++;
    if (s->count==1) { s->candidate=container_of(n,struct arm_pmu,cpu_pm_nb);s->index=index; }
    return 0;
}
