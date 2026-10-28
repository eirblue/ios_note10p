/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PMU_SETTLE_H
#define NOTE10_PMU_SETTLE_H
struct n10_pmu_settle_sample {
    unsigned int generation, completed, index, error, before, state, after;
};
int n10_pmu_settle_capture(struct n10_pmu_settle_sample *out,
                         unsigned int completed, unsigned int index);
int n10_pm_settle_capture(struct n10_pmu_settle_sample *out,
                        unsigned int completed, unsigned int index);
#endif
