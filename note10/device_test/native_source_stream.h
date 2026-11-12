/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_NATIVE_SOURCE_STREAM_H
#define NOTE10_NATIVE_SOURCE_STREAM_H
#include "native_source_ingest.h"
#include "native_source_sha256.h"
#define N226_SOURCE_CAP 6209536
#define N226_POOL_BYTES 49152
#define N226_WORKSPACE_BYTES 42312
#define N226_CONTROL_OFFSET 42312
#define N226_REQUEST_OFFSET 43000
#define N226_STAGE_OFFSET 45056
#define N226_STATS_OFFSET 43496
#define N226_CHAIN_CAP 8192U
#define N226_STACK_GUARD 4096U
#define N226_HEADER_BYTES 96
#define N226_RAW_CAP 19186176ULL
#define N226_NOINLINE __attribute__((__noinline__))
struct n226_role { n209_u64 offset,size,read; };
struct n226_stream {
    struct n226_role roles[2];
    n209_u64 member_bytes,compressed_cursor,raw_cursor,output_limit,current_role;
    n209_u32 flags,crc32,trailer_crc32,trailer_isize,header_have,parser_state;
    n209_u8 newc_header[110],name[18],gzip_header[10],gzip_trailer[8];
};
struct n226_codec {
    int (*begin)(void *);
    int (*pull)(void *,const n209_u8 *,unsigned int,n209_u8 *,unsigned int,unsigned int *,unsigned int *);
    n209_u32 (*crc)(n209_u32,const n209_u8 *,unsigned int);
    void (*end)(void *);
};
_Static_assert(sizeof(struct n226_stream)==264,"stream264");
_Static_assert(offsetof(struct n226_stream,newc_header)==112,"header112");
_Static_assert(offsetof(struct n226_stream,gzip_trailer)==250,"trailer250");
int n226_open(struct n226_stream *,const n209_u8 *,unsigned long,const n209_u8 *,struct n219_sha256 *,const struct n226_codec *,void *);
int n226_descriptor_digest(struct n219_sha256 *,const n209_u8 *,n209_u8 *);
int n226_stack_room(n209_u64,n209_u64,n209_u64,unsigned int,unsigned int);
long n226_read(struct n226_stream *,const n209_u8 *,unsigned int,n209_u64,void *,unsigned int,const struct n226_codec *,void *);
#endif
