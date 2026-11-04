/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_LEGACY_KEXEC_CORE_H
#define N10_LEGACY_KEXEC_CORE_H
#ifdef __KERNEL__
#include <linux/types.h>
typedef u64 n10_u64;
typedef u32 n10_u32;
typedef u8 n10_u8;
#else
typedef unsigned long long n10_u64;
typedef unsigned int n10_u32;
typedef unsigned char n10_u8;
#endif
#define N10_KEXEC_BYTES (32ULL << 20)
#define N10_KEXEC_ALIGN 16384ULL
#define N10_KEXEC_LIMIT (1ULL << 40)
#define N10_KEXEC_MIN (1ULL << 31)
#define N10_KEXEC_ARCH (183UL << 16)
struct n10_destination {
    char magic[8];
    n10_u32 schema, bytes;
    n10_u64 base, size;
    n10_u8 cookie[16];
    char build[32];
    n10_u64 reserved_pages, valid_pages;
    n10_u32 page_shift, status;
    n10_u64 generation;
    n10_u8 reserved[16];
};
_Static_assert(sizeof(struct n10_destination) == 128, "destination wire128");
struct n10_kexec_segment { const void *buf; n10_u64 bufsz; const void *mem; n10_u64 memsz; };
_Static_assert(sizeof(void *) == 8, "64-bit producer and host fixture required");
_Static_assert(sizeof(struct n10_kexec_segment) == 32, "native64 kexec segment32");
struct n10_reserve_ops {
    n10_u64 (*find)(void *, n10_u64, n10_u64, n10_u64, n10_u64);
    int (*memory)(void *, n10_u64, n10_u64);
    int (*reserved)(void *, n10_u64, n10_u64);
    int (*reserve)(void *, n10_u64, n10_u64);
};
struct n10_loader_ops {
    long (*arm)(void *, const struct n10_destination *);
    long (*load)(void *, n10_u64, n10_u64, const struct n10_kexec_segment *, n10_u64);
    long (*reboot)(void *);
    void (*cancel)(void *, const struct n10_destination *);
};
struct n10_marker_ops { int (*read)(void *, int, n10_u32 *); int (*write)(void *, int, n10_u32); };
struct n10_wdt_witness {
    n10_u32 present, variant_bound, enabled, reset_enabled, interrupt_only, pmu_route_enabled;
    n10_u64 clock_rate;
    n10_u32 data, first_count, last_count, effective_timeout;
};
int n10_reserve_destination(const struct n10_reserve_ops *, void *, n10_u64 *);
int n10_destination_valid(const struct n10_destination *, const char *);
long n10_loader_proof(const struct n10_destination *, const char *, const void *, unsigned long,
                      const struct n10_loader_ops *, void *);
int n10_stage_marker(const struct n10_marker_ops *, void *, n10_u32, n10_u32, n10_u32);
int n10_watchdog_qualified(const struct n10_wdt_witness *);
#endif
