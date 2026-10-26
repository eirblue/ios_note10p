/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_TEST_CONTRACT_H
#define NOTE10_PM_TEST_CONTRACT_H
struct n10_pm_result {
    unsigned int devices, resumed, blocked, old_level, new_level;
    unsigned int resume_errors_before, resume_errors_after;
    unsigned int stage;
    int error;
};
int n10_pm_devices_test(struct n10_pm_result *out);
#endif
