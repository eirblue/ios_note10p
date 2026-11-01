/* SPDX-License-Identifier: GPL-2.0-only */
/* Diagnostic-only composition; original recovery and v70 KAT bytes stay intact. */
#include <crypto/hash.h>
#include <linux/atomic.h>
#include <linux/err.h>
#include <linux/init.h>
#include <linux/jiffies.h>
#include <linux/kernel.h>
#include <linux/reboot.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/workqueue.h>
#include "note10_sha256_kat_id.h"
#define N10_RESERVE_BUILD_ID N10_SHA256_KAT_ID

/* Same FNV-1a frame checksum contract used by the existing recovery decoder. */
static u32 n10_frame_checksum(const char *text, unsigned int length)
{
    u32 value = 2166136261U;
    unsigned int i;
    for (i = 0; i < length; i++)
        value = (value ^ (unsigned char)text[i]) * 16777619U;
    return value;
}
#include "note10_auto_return.c"

/* All inherited headers have been included above. Keep inherited C byte-exact,
 * while giving its callback permanent lifetime and removing its old initcall.
 * Restore both macros before defining this integration's sole late initcall. */
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
