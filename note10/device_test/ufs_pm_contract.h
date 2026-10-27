/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_UFS_PM_CONTRACT_H
#define NOTE10_UFS_PM_CONTRACT_H
struct n10_ufs_pm_sample {
    unsigned int phase, generation, seen, error;
    unsigned long long requests, tasks, lrb;
    unsigned int hci_seen, hci_error, hce, transfer_db, task_db;
    unsigned int powered, irq, system, busy, power, link, clock, gating, runtime;
};
struct ufs_hba;
void n10_ufs_hci_arm(struct ufs_hba *hba, unsigned int generation);
void n10_ufs_hci_before_clock_off(struct ufs_hba *hba, unsigned int pm_op);
void n10_ufs_hci_finish(struct ufs_hba *hba, unsigned int generation, struct n10_ufs_pm_sample *out);
void n10_ufs_pm_capture(unsigned int phase, unsigned int generation);
int n10_ufs_pm_read(struct n10_ufs_pm_sample *out, unsigned int completed);
#endif
