/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_TEST_CONTRACT_H
#define NOTE10_PM_TEST_CONTRACT_H
struct n10_pm_result {
    unsigned int devices, resumed, blocked, old_level, new_level;
    unsigned int resume_errors_before, resume_errors_after;
    unsigned int stage;
    int error;
    int screen_error, display_error, usb_error, wake_error;
    int usb_restore_error, display_restore_error, screen_restore_error;
    unsigned int qphase, qgeneration, cable_epoch;
    unsigned int pm_called, quiesce_restored;
    unsigned int decon_cookie, usb_cookie;
};
int n10_pm_devices_test(struct n10_pm_result *out);
#endif
