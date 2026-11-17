/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_V290_PREPARATION_STORAGE_H
#define NOTE10_V290_PREPARATION_STORAGE_H
#include "v278_current_owner_seal.h"
#define N290_STORAGE_OFFSET 44896U
#define N290_STORAGE_BYTES (3ULL*N209_PAGE)
enum n290_phase { N290_EMPTY, N290_REFUSED, N290_INITIALIZING, N290_STORAGE_PREPARED, N290_QUARANTINED };
/* Inert current-preparation storage only; never a transfer capability. The
 * digest is the ORIGINAL sealed request.payload digest, not this record's hash. */
struct n290_storage {
    n209_u32 phase,flags;
    n209_u64 generation,base,size,prior_top,args_offset,adt_offset,record_offset,end_offset;
    n209_u8 cookie[16],descriptor_sha256[32],reserved[40];
};
_Static_assert(sizeof(struct n290_storage)==160,"storage160");
_Static_assert(__alignof__(struct n290_storage)==8,"storagealign8");
_Static_assert(N290_STORAGE_OFFSET%8==0&&N290_STORAGE_OFFSET+160==45056,"existing tail only");
int n290_plan_storage(struct n290_storage *,const struct n278_seal *,const struct n210_request *,
    const struct n210_destination *,const struct n210_context *,const struct n210_receipt *);
#endif
