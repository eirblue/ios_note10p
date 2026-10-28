/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_EDGE_IOMMU_H
#define NOTE10_PM_EDGE_IOMMU_H
struct n10_edge_iommu_detail {
    char name[64];
    unsigned int length, activations, runtime_count, manual, active, suspended;
    unsigned int effective, syscore, direct, prepared, pm_suspended, late, noirq, hold, secure, mapped;
};
struct n10_edge_iommu_sample {
    unsigned int phase, generation, seen, error, total;
    unsigned int active, suspended, runtime, manual_off, manual_on;
    unsigned int boot_hold, secure_configured, mapped;
    unsigned int syscore, direct, prepared, pm_suspended, late, noirq, runtime_other;
    unsigned int names_xor, names_sum;
    unsigned int policy_active, detail_count;
    struct n10_edge_iommu_detail details[8];
};
void n10_edge_iommu_capture(unsigned int phase, unsigned int generation);
int n10_edge_iommu_read(struct n10_edge_iommu_sample *out, unsigned int completed);
#endif
