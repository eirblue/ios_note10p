/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_ABOX_PMU_CONTRACT_H
#define NOTE10_ABOX_PMU_CONTRACT_H
struct n10_abox_pmu_sample {
    unsigned int phase, generation, seen, error, count;
    unsigned int power[2], enable[2], standby[2];
};
void n10_abox_pmu_capture(unsigned int phase, unsigned int generation);
int n10_abox_pmu_read(struct n10_abox_pmu_sample *out, unsigned int completed);
#endif
