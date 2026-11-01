/* SPDX-License-Identifier: GPL-2.0-only */
#ifdef CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION
#include <linux/atomic.h>
#include <linux/errno.h>
#include <linux/init.h>
#include <linux/jiffies.h>
#include <linux/kernel.h>
#include <linux/random.h>
#include <linux/reboot.h>
#include <linux/sched.h>
#include <linux/string.h>
#include <linux/workqueue.h>
#include "note10_sha256_kat_id.h"
#define N10_RESERVE_BUILD_ID N10_SHA256_KAT_ID
static char n10_boot_id[33];
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
#include "native_memory_observation.c"
#define n10_sha256_kat_init n10_memory_emit
#include "sha256_kat_recovery_work.c"
#undef n10_sha256_kat_init
#pragma pop_macro("pr_info")
#include "builtin_init_route.c"
#endif
