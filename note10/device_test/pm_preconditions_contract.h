/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_PRECONDITIONS_H
#define NOTE10_PM_PRECONDITIONS_H
#include <linux/types.h>
struct notifier_block;
#define N10_PRECOND_CAP 32
#define N10_PRECOND_FIELDS 8
enum n10_precond_kind { N10_PRE_UNKNOWN, N10_PRE_GIC, N10_PRE_TIMER, N10_PRE_FPSIMD, N10_PRE_SUGOV, N10_PRE_PMU, N10_PRE_EHLD };
struct n10_precond_row { int priority; unsigned int kind, valid; s64 value[N10_PRECOND_FIELDS]; };
struct n10_precond_sample { unsigned int generation, seen, bad, completed, count; int error; struct n10_precond_row row[N10_PRECOND_CAP]; };
struct n10_precond_gic_row { u32 enable, active, config[2], priority[8]; unsigned int seen, restore_matches; };
struct n10_precond_gic_sample { unsigned int generation, seen, bad, completed; int error; struct n10_precond_gic_row phase[3]; };
int n10_pre_gic(struct notifier_block *, struct n10_precond_row *);
int n10_pre_timer(struct notifier_block *, struct n10_precond_row *);
int n10_pre_fpsimd(struct notifier_block *, struct n10_precond_row *);
int n10_pre_sugov(struct notifier_block *, struct n10_precond_row *);
int n10_pre_pmu(struct notifier_block *, struct n10_precond_row *);
int n10_pre_ehld(struct notifier_block *, struct n10_precond_row *);
int n10_pre_context(unsigned int generation, int irq_off, unsigned int preempt);
int n10_pre_chain(struct n10_precond_sample *, unsigned int generation);
int n10_pre_gic_regs(unsigned int phase, struct n10_precond_gic_row *, u32 cpu_ctlr, u32 pmr);
int n10_pre_gic_step(unsigned int generation, unsigned int phase, u32 ctlr, u32 pmr);
int n10_pre_gic_read(struct n10_precond_gic_sample *, unsigned int completed);
int n10_pre_capture(unsigned int generation);
int n10_pre_read(struct n10_precond_sample *, unsigned int completed);
#endif
