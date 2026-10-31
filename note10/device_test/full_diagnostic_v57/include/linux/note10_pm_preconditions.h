/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_PRECONDITIONS_H
#define NOTE10_PM_PRECONDITIONS_H
#include <linux/types.h>
struct notifier_block;
#define N10_PRECOND_CAP 32
#define N10_PRECOND_FIELDS 8
enum n10_precond_kind { N10_PRE_UNKNOWN, N10_PRE_GIC, N10_PRE_TIMER, N10_PRE_FPSIMD, N10_PRE_SUGOV, N10_PRE_PMU, N10_PRE_EHLD };
struct n10_precond_row { int priority; unsigned int kind, valid; s64 value[N10_PRECOND_FIELDS]; };
#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE
/* Scalar record only. Nibbles encode admitted roster indices 1..6. */
struct n10_cpu_pm_dispatch_sample {
 unsigned int generation, roster, phases, conflict, valid;
 unsigned int entered[2], returned[2], entry_order[2], return_order[2];
};
void n10_dispatch_begin(unsigned int generation);
void n10_dispatch_seed(unsigned int index, struct notifier_block *node);
void n10_dispatch_arm(struct notifier_block **head, unsigned long event, unsigned int phase);
void n10_dispatch_disarm(struct notifier_block **head, unsigned long event);
void n10_dispatch_finish(struct n10_cpu_pm_dispatch_sample *out);
#endif
struct n10_cpu_pm_roundtrip_sample {
 unsigned int generation, attempted, chain_lock_acquired, chain_lock_released;
 unsigned int roster_count, roster_valid, pre_snapshot_valid, post_snapshot_valid;
 unsigned int cpu_before, online_before, online_count_before;
 unsigned int enter_calls, exit_calls, enter_succeeded, exit_succeeded;
 unsigned int daif_stable, timer_stable, gic_stable, ehld_before, ehld_after, context_stable, passed;
 unsigned int terminal_attempted, terminal_recorded, terminal_completed;
 unsigned int caller_invoked, terminal_stage;
 int terminal_outer_error, terminal_helper_error, terminal_probe_error;
 int enter_error, exit_error, error;
#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE
 struct n10_cpu_pm_dispatch_sample dispatch;
#endif
#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_COUNTS
 unsigned int notifier_count_capture_valid, notifier_count_conflict;
 unsigned int enter_nr_calls_seen, exit_nr_calls_seen;
 int enter_nr_calls, exit_nr_calls;
#endif
};
struct n10_precond_sample { unsigned int generation, seen, bad, completed, count; int error; struct n10_precond_row row[N10_PRECOND_CAP]; 
#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
    struct n10_cpu_pm_roundtrip_sample roundtrip;
#endif
};
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
#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
int n10_cpu_pm_roundtrip(unsigned int, const struct n10_precond_sample *, struct n10_cpu_pm_roundtrip_sample *);
int n10_pre_roundtrip_terminal_read(struct n10_cpu_pm_roundtrip_sample *, unsigned int completed);
#endif
int n10_pre_gic_regs(unsigned int phase, struct n10_precond_gic_row *, u32 cpu_ctlr, u32 pmr);
int n10_pre_gic_step(unsigned int generation, unsigned int phase, u32 ctlr, u32 pmr);
int n10_pre_gic_read(struct n10_precond_gic_sample *, unsigned int completed);
int n10_pre_capture(unsigned int generation);
int n10_pre_read(struct n10_precond_sample *, unsigned int completed);
#endif
