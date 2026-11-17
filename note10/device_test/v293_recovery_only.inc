/* SPDX-License-Identifier: GPL-2.0-only */
/* Permanent text: SYSTEM_RUNNING caller parks before PID1. The existing
 * dedicated 90-second worker remains the only recovery-request owner. */
void __noreturn n293_recovery_only(void)
{
    unsigned int sequence = 0;

    for (;;) {
        if (sequence < 12) {
            printk(KERN_INFO "N293RET id=%s boot=%s cycle=%s stage=park seq=%u arm=%d requested=%d running=%u\n",
                   N154_BUILD_ID, n10_boot_id, (const char *)n10_cycle,
                   sequence++, READ_ONCE(n154_arm_result),
                   atomic_read(&n10_return_requested),
                   (unsigned int)(READ_ONCE(system_state) == SYSTEM_RUNNING));
        }
        /* Sleeping the init task leaves timer/workqueue scheduling available. */
        schedule_timeout_uninterruptible(10 * HZ);
    }
}
