/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_V278_CURRENT_OWNER_SEAL_H
#define NOTE10_V278_CURRENT_OWNER_SEAL_H
#include "native_source_ingest.h"
enum n278_phase { N278_EMPTY=0, N278_VALUES_ONLY=1, N278_REFUSED=2 };
struct n278_values {
    struct n210_request request;
    struct n210_context context;
    struct n210_receipt prepared;
    struct n217_result ingested;
    struct n209_layout layout;
    n209_u64 adapter_entry;
};
struct n278_seal { unsigned int phase; struct n278_values values; };
/* Caller owns valid disjoint spans and a zero-initialized seal exclusively.
 * Future owner-TU call: after n226 success, with n210_lock held and request
 * still live, before cleanup/unlock. Installed277 does not call this function.
 * descriptor_hash is the retained owner's computed digest of this payload.
 * This copies values only: no mapping, metadata or independent-return grant. */
int n278_seal_once(struct n278_seal *,const struct n210_request *,
    const struct n210_destination *,const struct n210_context *,const n209_u8 *,
    const struct n210_receipt *,unsigned int,const struct n217_state *);
#endif
