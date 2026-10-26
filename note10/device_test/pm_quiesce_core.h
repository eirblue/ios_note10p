/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_QUIESCE_CORE_H
#define NOTE10_PM_QUIESCE_CORE_H
/* Phase identifiers emitted by the actual kernel transaction backend. */
enum n10_qphase {
    N10_Q_IDLE, N10_Q_OWNER, N10_Q_SCREEN, N10_Q_DISPLAY_OFF,
    N10_Q_USB_BLOCKED, N10_Q_WAKE_CLEAR, N10_Q_PM_ENTERED,
    N10_Q_RESTORE_USB, N10_Q_RESTORE_DISPLAY, N10_Q_RESUME_SCREEN,
    N10_Q_DONE, N10_Q_FAILED
};
#endif
