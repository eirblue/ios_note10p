/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_NATIVE_PARCEL_CORE_H
#define NOTE10_NATIVE_PARCEL_CORE_H
#ifdef __KERNEL__
#include <linux/types.h>
#include <linux/stddef.h>
typedef u64 n209_u64;
typedef u32 n209_u32;
typedef u8 n209_u8;
#else
#include <stdint.h>
#include <stddef.h>
typedef uint64_t n209_u64;
typedef uint32_t n209_u32;
typedef uint8_t n209_u8;
#endif

#define N209_PAGE 16384ULL
#define N209_DESTINATION_BYTES (32ULL << 20)
#define N209_ADDRESS_LIMIT (1ULL << 40)
#define N209_ADDRESS_MIN (1ULL << 31)
#define N209_ADT_MAX (1ULL << 20)
#define N209_BOOT_ARGS_BYTES 1152ULL
#define N209_PAYLOAD_BYTES 256U

/* Little-endian source recipe. No address reservation or execution authority. */
struct n209_payload {
    n209_u8 magic[8];
    n209_u32 schema, bytes;
    n209_u64 virtual_base, kernel_span, kernel_entry_offset;
    n209_u64 entry_extent_offset, entry_extent_bytes, pool_offset, pool_bytes;
    n209_u64 adapter_bytes, adapter_entry_offset, adapter_record_offset;
    n209_u8 kernel_sha256[32], materialized_sha256[32], adapter_sha256[32];
    n209_u8 producer_id[32], input_binding[32];
};
struct n209_destination {
    n209_u64 base, size, generation;
    n209_u32 page_shift, status;
    n209_u8 build[32], cookie[16];
};
struct n209_layout {
    n209_u64 args_offset, adt_offset, adt_bytes, adapter_offset, top_offset;
};
/* Future callers must obtain these facts from real owners/return consumers.
 * A host callback success proves only the fixture's metadata predicates. */
struct n209_prerequisites {
    int (*source_live)(void *, const struct n209_payload *);
    int (*destination_current)(void *, const struct n209_destination *);
    int (*return_qualified)(void *);
};

_Static_assert(sizeof(struct n209_payload) == 256, "native payload wire256");
_Static_assert(offsetof(struct n209_payload, virtual_base) == 16, "wire scalar offset");
_Static_assert(offsetof(struct n209_payload, kernel_sha256) == 96, "wire kernel hash offset");
_Static_assert(offsetof(struct n209_payload, materialized_sha256) == 128, "wire memory hash offset");
_Static_assert(offsetof(struct n209_payload, adapter_sha256) == 160, "wire adapter hash offset");
_Static_assert(offsetof(struct n209_payload, producer_id) == 192, "wire producer offset");
_Static_assert(offsetof(struct n209_payload, input_binding) == 224, "wire input binding offset");
_Static_assert(sizeof(struct n209_destination) == 80, "destination facts80");
_Static_assert(sizeof(struct n209_layout) == 40, "relative layout40");

int n209_decode_payload(const n209_u8 *, unsigned long, struct n209_payload *);
int n209_prepare_layout(const struct n209_payload *, const struct n209_destination *,
                       n209_u64, const struct n209_prerequisites *, void *, struct n209_layout *);
#endif
