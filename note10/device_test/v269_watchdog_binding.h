/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_V269_WATCHDOG_BINDING_H
#define NOTE10_V269_WATCHDOG_BINDING_H
#ifdef __KERNEL__
#include <linux/types.h>
typedef u32 n269_u32;
typedef u64 n269_u64;
#else
#include <stdint.h>
#include <stddef.h>
typedef uint32_t n269_u32;
typedef uint64_t n269_u64;
#endif
#define N269_POOL_OFFSET 43664U
enum { N269_UNSEEN, N269_PROBING, N269_PUBLISHED, N269_REMOVED,
       N269_AMBIGUOUS, N269_BUSY, N269_BAD_CONTEXT };
enum { N269_TAIL=1, N269_REGISTER_OK=2, N269_CORE=4, N269_RATE=8,
       N269_GATE=16, N269_CALLBACK=32, N269_SOFT=64, N269_MULTI=128 };
struct n269_binding {
    n269_u64 probe_cached_rate_hz;
    n269_u32 schema,state,error_code,cluster,variant,flags,watchdog_id_at_probe,reserved;
};
_Static_assert(sizeof(struct n269_binding)==40,"binding40");
_Static_assert(__alignof__(struct n269_binding)==8,"bindingalign8");
_Static_assert(__builtin_offsetof(struct n269_binding,state)==12,"state12");
_Static_assert(__builtin_offsetof(struct n269_binding,reserved)==36,"reserved36");
int n269_snapshot(struct n269_binding *);
#endif
