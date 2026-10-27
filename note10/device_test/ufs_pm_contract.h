/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_UFS_PM_CONTRACT_H
#define NOTE10_UFS_PM_CONTRACT_H
struct n10_ufs_pm_sample {
    unsigned int phase, generation, seen, error;
    unsigned long long requests, tasks, lrb;
    unsigned int powered, irq, system, busy, power, link, clock, gating, runtime;
};
void n10_ufs_pm_capture(unsigned int phase, unsigned int generation);
int n10_ufs_pm_read(struct n10_ufs_pm_sample *out, unsigned int completed);
#endif
