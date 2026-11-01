/* SPDX-License-Identifier: GPL-2.0-only */
#include <crypto/hash.h>
#include <linux/atomic.h>
#include <linux/err.h>
#include <linux/init.h>
#include <linux/jiffies.h>
#include <linux/kernel.h>
#include <linux/random.h>
#include <linux/reboot.h>
#include <linux/sched.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/workqueue.h>
#include "note10_sha256_kat_id.h"
#define N10_RESERVE_BUILD_ID N10_SHA256_KAT_ID
static char n10_boot_id[33];
static u32 n10_frame_checksum(const char *text, unsigned int length)
{
    u32 value = 2166136261U;
    unsigned int i;
    for (i = 0; i < length; i++)
        value = (value ^ (unsigned char)text[i]) * 16777619U;
    return value;
}
/* Add transport-level boot association without changing inherited frame bytes
 * or checksum bodies. Prefix validation belongs to the distinct v72 profile. */
#pragma push_macro("pr_info")
#undef pr_info
#define pr_info(fmt, ...) printk(KERN_INFO "N10BOOTLINK2 boot=%s " fmt, n10_boot_id, ##__VA_ARGS__)
#include "note10_auto_return.c"
#pragma push_macro("__init")
#pragma push_macro("late_initcall")
#undef __init
#undef late_initcall
#define __init
#define late_initcall(fn)
#include "sha256_runtime_kat.c"
#pragma pop_macro("late_initcall")
#pragma pop_macro("__init")
#include "sha256_kat_recovery_work.c"
#pragma pop_macro("pr_info")
#include "builtin_init_route.c"
