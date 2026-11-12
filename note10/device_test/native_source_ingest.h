/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_NATIVE_SOURCE_INGEST_H
#define NOTE10_NATIVE_SOURCE_INGEST_H
#include "native_prepare_core.h"
#define N217_CHUNK 4096U
/* New source-consumption association; no execution or native mapping ticket. */
struct n217_request { n209_u8 magic[8];n209_u32 schema,bytes;struct n210_request prepared; };
struct n217_result {
    n209_u8 magic[8];n209_u32 schema,bytes,status,error_code,flags,reserved;
    n209_u64 generation;n209_u8 build[32],boot[32],cycle[32],cookie[16];
    n209_u64 source_bytes[2],copied_bytes[2];
    n209_u8 source_sha256[2][32],destination_sha256[2][32];
    n209_u64 source_data_bytes,staging_request_bytes;
    n209_u32 files_held,destination_content_verified,quarantined,source_pages_physically_pinned;
    n209_u8 tail[8];
};
struct n217_state { unsigned int spent;void *held[2];n209_u64 inode[2];struct n217_result result; };
/* Fixed two-role boundary. Host implementations prove only fixture ordering. */
struct n217_io {
    int (*owner)(void *,const struct n210_destination *);
    int (*hold)(void *,unsigned int,n209_u64,void **,n209_u64 *);
    long (*read)(void *,void *,n209_u64,void *,unsigned int);
    void (*put)(void *,void *);
    int (*hash_begin)(void *);
    int (*hash_update)(void *,const void *,unsigned int);
    int (*hash_end)(void *,n209_u8 *);
    int (*write_destination)(void *,n209_u64,const void *,unsigned int);
    int (*read_destination)(void *,n209_u64,void *,unsigned int);
    int (*clear_destination)(void *,n209_u64,n209_u64);
};
_Static_assert(sizeof(struct n217_request)==496,"source request496");
_Static_assert(offsetof(struct n217_request,prepared)==16,"prepared offset16");
_Static_assert(sizeof(struct n217_result)==352,"source receipt352");
_Static_assert(offsetof(struct n217_result,source_sha256)==184,"source digests184");
_Static_assert(offsetof(struct n217_result,destination_sha256)==248,"destination digests248");
int n217_consume(const struct n217_request *,const struct n210_destination *,const struct n210_context *,
                 const struct n210_receipt *,struct n217_state *,const struct n217_io *,void *,n209_u8 *,unsigned int);
#ifdef __KERNEL__
int n217_ingest_current(const struct n217_request *,struct n217_result *);
#endif
#endif
