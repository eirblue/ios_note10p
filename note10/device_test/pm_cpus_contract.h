/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_CPUS_H
#define NOTE10_PM_CPUS_H
#include <linux/note10_abox_pmu.h>
struct n10_pm_cpus_sample {
    unsigned int generation, seen, bad, attempted, disabled, enabled;
    unsigned int before, stopped, restored, cpu, phase;
    int original_error, error;
};
int n10_pm_cpus_roundtrip(unsigned int generation);
int n10_pm_cpus_read(struct n10_pm_cpus_sample *out,
                     struct n10_pmu_noirq_sample *pmu, unsigned int completed);
void n10_pmu_cpu_capture(unsigned int generation);
int n10_pmu_cpu_read(struct n10_pmu_noirq_sample *out, unsigned int completed);
#endif
