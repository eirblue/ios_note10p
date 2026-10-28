/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_BRANCH_H
#define NOTE10_PM_BRANCH_H
#include <linux/types.h>
struct notifier_block;
#define N10_BRANCH_CAP 32
struct n10_branch_row {unsigned int index,kind,num,supported,reset,start,stop;u32 used,nonnull,match;};
struct n10_branch_sample {unsigned int generation,seen,completed,count;int error;struct n10_branch_row row[N10_BRANCH_CAP];};
int n10_branch_ehld_equal(const void *event);
int n10_branch_pmu(struct notifier_block *,struct n10_branch_row *);
void n10_branch_invalidate(void);
void n10_branch_begin(unsigned int generation);
int n10_branch_collect(struct notifier_block *,unsigned int index,unsigned int kind);
void n10_branch_finish(int error);
int n10_branch_copy(struct n10_branch_sample *,unsigned int completed);
int n10_branch_read(struct n10_branch_sample *,unsigned int completed);
#endif
