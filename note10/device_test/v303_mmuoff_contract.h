/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N303_MMUOFF_CONTRACT_H
#define N303_MMUOFF_CONTRACT_H
#define N303_RECORD_BYTES 250
#define N303_BODY_OFFSET 9
#define N303_BODY_BYTES 222
#define N303_EL_OFFSET 125
#define N303_SCTLR_OFFSET 133
#define N303_CHECKSUM_OFFSET 241
#define N303_COMMIT_OFFSET 7
#define N303_PARAM_TEXT 32
#ifndef __ASSEMBLY__
#ifdef __KERNEL__
#include <linux/types.h>
typedef u64 n303_u64;
#else
typedef unsigned long long n303_u64;
#endif
#define N303_FORMAT "N303POS0 id=%s boot=%s cycle=%s el=0 sctlr=0000000000000000 slot=%016llx cursor=%016llx next=%016llx tail=%08llx checksum=00000000\n"
struct n303_owner { n303_u64 log_pa,log_va,log_bytes,cursor_va,header_pa,header_va,header_bytes,saved,offset;unsigned int enabled; };
struct n303_slot { n303_u64 record,cursor,next,tail; };
struct n303_parameters { n303_u64 record,cursor,next,bytes;char text[N303_RECORD_BYTES+1]; };
static inline int n303_claim_ok(const struct n303_owner *s,struct n303_slot *out)
{
    n303_u64 log_end,header_end,position,tail;
    if(!s->enabled || !s->log_pa || !s->log_va || !s->header_pa || !s->header_va ||
       s->log_bytes<8+N303_RECORD_BYTES || s->log_bytes>0xffffffffULL || s->header_bytes<4 ||
       s->offset>s->header_bytes-4 || s->log_pa>~0ULL-s->log_bytes || s->header_pa>~0ULL-s->header_bytes ||
       s->log_va>~0ULL-s->log_bytes)return 0;
    log_end=s->log_pa+s->log_bytes;header_end=s->header_pa+s->header_bytes;
    if(!(log_end<=s->header_pa || header_end<=s->log_pa) || s->cursor_va<s->log_va ||
       s->cursor_va-s->log_va>s->log_bytes-8-N303_RECORD_BYTES)return 0;
    position=s->log_pa+(s->cursor_va-s->log_va);tail=log_end-8-position;
    if(s->saved!=position || position>0xffffffffULL-N303_RECORD_BYTES || ((s->header_pa+s->offset)&3))return 0;
    out->record=position;out->cursor=s->header_pa+s->offset;out->next=position+N303_RECORD_BYTES;out->tail=tail;
    return 1;
}
#ifdef __KERNEL__
int n303_snapshot_claim(struct n303_slot *out);
int n303_enter(const char *build,const char *boot,const char *cycle);
#endif
#endif
#endif
