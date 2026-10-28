/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PMU_CONTROL_AUDIT_H
#define NOTE10_PMU_CONTROL_AUDIT_H
#include <linux/types.h>
struct notifier_block;
struct arm_pmu;
struct n10_ctl_row {
    unsigned int index, chain_count, kind, num;
    u32 used_sw, visible_phys, used_phys;
    unsigned int current_el, model_match, variant, revision, pmuver, fgt;
    u32 pmcr, cntenset, intenset;
};
struct n10_ctl_sample { unsigned int generation, seen, completed; int error; struct n10_ctl_row row; };
/* Stage is stack-local to the chain walk and never survives chain unlock. */
struct n10_ctl_stage { struct arm_pmu *candidate; unsigned int count,index; };
int n10_ctl_consider(struct notifier_block *,struct n10_ctl_stage *,unsigned int,unsigned int);
int n10_ctl_backend(struct arm_pmu *,struct n10_ctl_row *,unsigned int);
int n10_ctl_resolve(struct n10_ctl_stage *,unsigned int,unsigned int);
void n10_ctl_begin(unsigned int);
void n10_ctl_invalidate(void);
void n10_ctl_finish(int);
int n10_ctl_copy(struct n10_ctl_sample *,unsigned int);
int n10_ctl_read(struct n10_ctl_sample *,unsigned int);
#endif
