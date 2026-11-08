/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/errno.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/random.h>
#include <linux/sched.h>
#include <linux/string.h>
#include "v154_linux_id.h"
#define N10_RESERVE_BUILD_ID N154_BUILD_ID
#define N10_SHA256_KAT_ID N154_BUILD_ID
static char n10_boot_id[33];
static int n154_arm_result = -EINPROGRESS;
static u32 n10_frame_checksum(const char *text, unsigned int length)
{
    u32 value = 2166136261U;
    unsigned int i;
    for (i = 0; i < length; ++i)
        value = (value ^ (unsigned char)text[i]) * 16777619U;
    return value;
}
#pragma push_macro("pr_info")
#undef pr_info
#define pr_info(fmt, ...) printk(KERN_INFO "N10BOOTLINK2 boot=%s " fmt, n10_boot_id, ##__VA_ARGS__)
#include "note10_auto_return.c"
#pragma pop_macro("pr_info")
#include "builtin_init_route.c"

void n154_require_return_armed(void);

/* N154_ARM_FAILURE_GATE_BEGIN */
void n154_require_return_armed(void)
{
    int error = READ_ONCE(n154_arm_result);
    if (!error)
        return;
    /* init/main calls only after SYSTEM_RUNNING, before argv or PID1. */
    n10_return_record(3, 5);
    if (!atomic_cmpxchg(&n10_return_requested, 0, 1)) {
        n10_return_record(1, 0);
        kernel_restart("recovery");
        n10_return_record(2, 1);
    }
    /* A worker already owns recovery, or restart returned. Never retry. */
    n10_builtin_init_failed(error);
}
/* N154_ARM_FAILURE_GATE_END */

static int __init n154_return_init(void)
{
    int result = n10_arm_auto_return();
    WRITE_ONCE(n154_arm_result, result);
    pr_info("N154ARM id=%s boot=%s cycle=%s result=%d\n", N154_BUILD_ID,
            n10_boot_id, (const char *)n10_cycle, result);
    return 0;
}
late_initcall(n154_return_init);
