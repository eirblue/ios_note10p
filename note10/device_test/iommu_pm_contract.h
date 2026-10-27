/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_IOMMU_PM_CONTRACT_H
#define NOTE10_IOMMU_PM_CONTRACT_H
struct n10_iommu_pm_detail {
    char name[64];
    unsigned int length, activations, runtime_count, manual, active, suspended;
    unsigned int effective, syscore, prepared, pm_suspended, hold, secure, mapped;
};
struct n10_iommu_pm_sample {
    unsigned int phase, generation, seen, error, total;
    unsigned int active, suspended, runtime, manual_off, manual_on;
    unsigned int boot_hold, secure_configured, mapped;
    unsigned int syscore, prepared, pm_suspended, runtime_other;
    unsigned int names_xor, names_sum;
    unsigned int policy_active, detail_count;
    struct n10_iommu_pm_detail details[8];
};
void n10_iommu_pm_capture(unsigned int phase, unsigned int generation);
int n10_iommu_pm_read(struct n10_iommu_pm_sample *out, unsigned int completed);
#endif
