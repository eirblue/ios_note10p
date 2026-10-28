/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_NOIRQ_CONTRACT_H
#define NOTE10_PM_NOIRQ_CONTRACT_H
#include <linux/note10_abox_pmu.h>
struct n10_pm_noirq_sample {
    unsigned int generation, seen, bad, finished, stage, state, phase;
    unsigned int late, late_ok, noirq, noirq_ok, point, blocked, ops_mask;
    unsigned int pre_early, post_early, pre_noirq, post_noirq;
    int error, original_error;
};
void n10_pm_noirq_begin(int state);
int n10_pm_noirq_context(int state);
int n10_pm_noirq_ready(int state);
void n10_pm_noirq_note(unsigned int event, int result);
int n10_pm_noirq_finish(int result);
int n10_pm_noirq_read(struct n10_pm_noirq_sample *out,
                     struct n10_pmu_noirq_sample *pmu, unsigned int completed);
#endif
