/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_V230_BOOT_METADATA_H
#define NOTE10_V230_BOOT_METADATA_H
#include "native_parcel_core.h"
#include "runtime_relocation.h"

/* Numeric placement only: no live-owner capability or reserved-RAM pointer. */
struct n230_placement {
    struct n209_layout layout;
    n209_u64 arguments_physical, adt_physical, adt_virtual, adapter_physical;
    n209_u64 entry_physical, record_physical, top_physical;
};
_Static_assert(sizeof(struct n230_placement)==96,"projection96");
_Static_assert(offsetof(struct n230_placement,arguments_physical)==40,"addresses after layout40");
_Static_assert(offsetof(struct n230_placement,top_physical)==88,"projection last field");

/* Synthetic metadata projection. Caller buffers must be valid memory; every
 * output is unchanged on rejection. ADT bytes and source adapter are not copied.
 * This API neither checks live ownership nor authorizes using these addresses. */
int n230_project_metadata(const struct n209_payload *,const struct n209_destination *,
    const n209_u8 *,n209_u32,n209_u8 *,n209_u64,n209_u8 *,n209_u64,struct n230_placement *);
#endif
