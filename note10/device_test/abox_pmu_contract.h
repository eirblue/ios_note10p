/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_ABOX_PMU_CONTRACT_H
#define NOTE10_ABOX_PMU_CONTRACT_H
struct exynos_pm_domain;
struct n10_fsys_pm_sample {
    unsigned int registered, invalid, entries, exits, gates, allowed, denied, skipped;
    unsigned int controls, control_errors, completed, last_result, last_negative, last_skipped;
};
void n10_fsys_note(struct exynos_pm_domain *pd, unsigned int event, int result);
int n10_fsys_gate(struct exynos_pm_domain *pd);
void n10_fsys_pm_read(struct n10_fsys_pm_sample *out);
struct n10_abox_pmu_sample {
    struct n10_fsys_pm_sample fsys;
    unsigned int phase, generation, seen, error, count;
    unsigned int domain_before, domain_state, domain_after;
    unsigned int power[2], enable[2], standby[2];
};
void n10_abox_pmu_capture(unsigned int phase, unsigned int generation);
int n10_abox_pmu_read(struct n10_abox_pmu_sample *out, unsigned int completed);
#endif
