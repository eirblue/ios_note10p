/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PMU_STATE_AUDIT_H
#define NOTE10_PMU_STATE_AUDIT_H
#include <linux/types.h>
struct notifier_block;
#define N10_STATE_CAP 32
struct n10_state_row {
    unsigned int index,kind,num,supported;
    u32 used,present,owned,observed,running,stopped,uptodate,abnormal;
    u32 affinity0,unbound,other,oncpu0,active;
};
struct n10_state_sample {
    unsigned int generation,seen,completed,count;
    int error;
    struct n10_state_row row[N10_STATE_CAP];
};
int n10_state_pmu(struct notifier_block *,struct n10_state_row *,unsigned int);
void n10_state_invalidate(void);
void n10_state_begin(unsigned int generation);
int n10_state_collect(struct notifier_block *,unsigned int index,unsigned int kind,unsigned int generation);
void n10_state_finish(int error);
int n10_state_copy(struct n10_state_sample *,unsigned int completed);
int n10_state_read(struct n10_state_sample *,unsigned int completed);
#endif
