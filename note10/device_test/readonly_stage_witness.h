/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_READONLY_STAGE_WITNESS_H
#define N10_READONLY_STAGE_WITNESS_H
/* Reuses the outcome's decoded u32; no additional permanent or outcome state. */
enum n10_stage_event {
    N10_SW_HEADER_ENTER=1u<<0,N10_SW_HEADER_OK=1u<<1,
    N10_SW_DECODE_CALLED=1u<<2,N10_SW_DECODE_RETURNED=1u<<3,
    N10_SW_API_OK=1u<<4,N10_SW_LENGTH_ENTER=1u<<5,N10_SW_LENGTH_OK=1u<<6,
    N10_SW_HASH_CALLED=1u<<7,N10_SW_HASH_RETURNED=1u<<8,
    N10_SW_DIGEST_ENTER=1u<<9,N10_SW_DIGEST_OK=1u<<10,
    N10_SW_WORK_CLEAR_CALLED=1u<<11,N10_SW_WORK_CLEAR_RETURNED=1u<<12,
    N10_SW_WORK_FREE_CALLED=1u<<13,N10_SW_WORK_FREE_RETURNED=1u<<14,
    N10_SW_OUTPUT_CLEAR_CALLED=1u<<15,N10_SW_OUTPUT_CLEAR_RETURNED=1u<<16,
    N10_SW_OUTPUT_FREE_CALLED=1u<<17,N10_SW_OUTPUT_FREE_RETURNED=1u<<18,
    N10_SW_STREAM_OK=1u<<19
};
#define N10_SW_ALL ((1u<<20)-1)
#define N10_STAGE(out,event) ((out)->decoded|=(event))
#define N10_STAGE_CALLS(out) ((unsigned int)!!((out)->decoded&N10_SW_DECODE_CALLED))
static inline int n10_stage_format(uint32_t bits,char *frame,size_t capacity,
    const char *identity,const char *cycle)
{
    int count=snprintf(frame,capacity,
        "id=%s cycle=%s kind=stages schema=readonly-stage-witness-v1 bits=%08x work_cleanup=%s output_cleanup=%s ownership=0 hardware=0 executed=0",
        identity,cycle,bits,
        (bits&N10_SW_WORK_FREE_RETURNED) ? "void_returned" : "not_called",
        (bits&N10_SW_OUTPUT_FREE_RETURNED) ? "void_returned" : "not_called");
    if(count<1 || (size_t)count>=capacity || count>447) return 0;
    return count;
}
#endif
