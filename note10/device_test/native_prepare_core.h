/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_NATIVE_PREPARE_CORE_H
#define NOTE10_NATIVE_PREPARE_CORE_H
#include "native_parcel_core.h"
#define N210_SLOT_BYTES 4096U
#define N210_RESIDUE 0x1004000ULL
/* Metadata association only. No source bytes, active native mapping or transfer. */
struct n210_destination { n209_u8 magic[8]; n209_u32 schema, bytes; struct n209_destination region; };
struct n210_binding {
    n209_u8 magic[8]; n209_u32 schema, bytes;
    n209_u8 build[32], cycle[32], descriptor_sha256[32], reserved[16];
};
struct n210_request { struct n210_destination destination; n209_u8 payload[256]; struct n210_binding binding; };
struct n210_receipt {
    n209_u8 magic[8]; n209_u32 schema, bytes, status, reserved;
    n209_u64 generation; n209_u8 build[32], boot[32], cycle[32], cookie[16], descriptor_sha256[32];
    n209_u64 flags, tail_reserved;
};
struct n210_context { n209_u8 build[32], boot[32], cycle[32]; n209_u32 return_armed, page_reserved, pid1, cap_sys_boot; };
_Static_assert(sizeof(struct n210_destination)==96,"destination96");
_Static_assert(sizeof(struct n210_binding)==128,"binding128");
_Static_assert(sizeof(struct n210_request)==480,"request480");
_Static_assert(sizeof(struct n210_receipt)==192,"receipt192");
_Static_assert(offsetof(struct n210_request,payload)==96,"payload offset96");
_Static_assert(offsetof(struct n210_request,binding)==352,"binding offset352");
_Static_assert(offsetof(struct n210_receipt,descriptor_sha256)==144,"receipt digest144");
_Static_assert(sizeof(struct n210_context)==112,"local context112");
int n210_request_valid(const struct n210_request *,const struct n210_destination *,const struct n210_context *,const n209_u8 *);
int n210_prepare_once(const struct n210_request *,const struct n210_destination *,const struct n210_context *,const n209_u8 *,unsigned int *,struct n210_receipt *);
int n210_receipt_matches(const struct n210_receipt *,const struct n210_context *,const struct n210_request *);
#ifdef __KERNEL__
int n210_linux_context(struct n210_context *);
#endif
#endif
