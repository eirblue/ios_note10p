/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_NATIVE_SOURCE_SHA256_H
#define NOTE10_NATIVE_SOURCE_SHA256_H
#include "native_parcel_core.h"
struct n219_sha256 { n209_u32 state[8];n209_u64 count;n209_u8 buf[64];unsigned int finalized; };
void n219_sha256_init(struct n219_sha256 *);
int n219_sha256_update(struct n219_sha256 *,const void *,unsigned int);
int n219_sha256_final(struct n219_sha256 *,n209_u8 out[32]);
#endif
