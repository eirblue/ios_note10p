/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_RCU_CONTEXT_AUDIT_H
#define NOTE10_RCU_CONTEXT_AUDIT_H
#include <linux/types.h>
struct n10_precond_sample;
struct n10_rcu_row {
    unsigned int chain_count, watching, nesting_class, positive_headroom_two;
    unsigned int nmi_nonzero, task_nesting_nonzero, task_special_nonzero, irq_enter_disabled;
};
struct n10_rcu_sample { unsigned int generation, seen, completed; int error; struct n10_rcu_row row; };
int n10_rcu_get(struct n10_rcu_row *, unsigned int);
void n10_rcu_begin(unsigned int);
void n10_rcu_invalidate(void);
int n10_rcu_collect(const struct n10_precond_sample *, unsigned int);
void n10_rcu_finish(int);
int n10_rcu_copy(struct n10_rcu_sample *, unsigned int);
int n10_rcu_read(struct n10_rcu_sample *, unsigned int);
#endif
