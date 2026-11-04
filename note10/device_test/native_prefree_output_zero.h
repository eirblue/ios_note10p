/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_NATIVE_PREFREE_OUTPUT_ZERO_H
#define N10_NATIVE_PREFREE_OUTPUT_ZERO_H
#include "carrier_lzma.h"
/* Distinct native candidate, not a PC format. Single synchronous caller-local
 * scope. bytes is a historical allocated-capacity witness after data=NULL, NOT
 * live capacity or a capability. Only data with the proper flags permits reads.
 * Observation BEFORE vfree proves nothing about bytes AFTER vfree, reclamation,
 * secure erasure, physical contiguity, global RAM or ownership/handoff. */
struct n10_output_handle { unsigned char *data; uint32_t bytes,scanned,nonzero,flags; };
_Static_assert(sizeof(struct n10_output_handle)==24,"prefree handle24");
_Static_assert(N10_LZMA_MAX_BYTES<=UINT32_MAX,"existing capacity fits counters");
enum { N10_OUT_OFFERED=1u<<0,N10_OUT_BORROWED=1u<<1,N10_OUT_FIRST_RETURNED=1u<<2,
    N10_OUT_LAST_RETURNED=1u<<3,N10_OUT_RELEASED=1u<<4,N10_OUT_RETIRED=1u<<5,
    N10_OUT_CLEAR_CALLED=1u<<6,N10_OUT_CLEAR_RETURNED=1u<<7,N10_OUT_FREE_CALLED=1u<<8,
    N10_OUT_FREE_RETURNED=1u<<9,N10_OUT_REFUSED=1u<<10,
    N10_OUT_SCAN_CALLED=1u<<11,N10_OUT_SCAN_RETURNED=1u<<12,N10_OUT_ZERO_OBSERVED=1u<<13 };
#define N10_OUT_ALL ((1u<<10)-1)
#ifndef N10_OUTPUT_READ_ONCE
#define N10_OUTPUT_READ_ONCE(x) READ_ONCE(x)
#endif
#ifndef N10_PREFREE_READ_ONCE
#define N10_PREFREE_READ_ONCE(x) READ_ONCE(x)
#endif
static inline int n10_output_offer(struct n10_output_handle *h,unsigned char *data,size_t bytes)
{
    if(!h || h->data || h->bytes || h->scanned || h->nonzero || h->flags || !data || !bytes ||
        bytes>N10_LZMA_MAX_BYTES || (uintptr_t)data>UINTPTR_MAX-bytes) return -1;
    h->data=data;h->bytes=(uint32_t)bytes;h->flags=N10_OUT_OFFERED;return 0;
}
static inline int n10_output_read_and_release(struct n10_output_handle *h)
{
    const unsigned char *p;
    if(!h || h->flags!=N10_OUT_OFFERED || !h->data || !h->bytes || h->bytes>N10_LZMA_MAX_BYTES ||
        (uintptr_t)h->data>UINTPTR_MAX-h->bytes) { if(h)h->flags|=N10_OUT_REFUSED;return -1; }
    p=h->data;h->flags|=N10_OUT_BORROWED;
    (void)N10_OUTPUT_READ_ONCE(p[0]);h->flags|=N10_OUT_FIRST_RETURNED;
    (void)N10_OUTPUT_READ_ONCE(p[h->bytes-1]);h->flags|=N10_OUT_LAST_RETURNED;
    h->flags|=N10_OUT_RELEASED;return 0;
}
/* Only an existing allocation owner calls this after its existing clear returns,
 * and before its matching existing free. No allocation, clear, free or retries. */
static inline int n10_output_observe_prefree(struct n10_output_handle *h,const unsigned char *p,size_t capacity)
{
    size_t i;
    if(!h || !p || !capacity || capacity>N10_LZMA_MAX_BYTES ||
        (uintptr_t)p>UINTPTR_MAX-capacity || (h->flags&N10_OUT_SCAN_CALLED) || h->scanned || h->nonzero ||
        !(h->flags&N10_OUT_CLEAR_RETURNED) || (h->flags&N10_OUT_FREE_CALLED) ||
        (h->data && (h->data!=p || h->bytes!=capacity))) return -1;
    h->bytes=(uint32_t)capacity;h->flags|=N10_OUT_SCAN_CALLED;
    for(i=0;i<capacity;++i) { unsigned char value=N10_PREFREE_READ_ONCE(p[i]);++h->scanned;if(value)++h->nonzero; }
    h->flags|=N10_OUT_SCAN_RETURNED;
    if(!h->nonzero)h->flags|=N10_OUT_ZERO_OBSERVED;
    return h->nonzero ? -1 : 0;
}
static inline int n10_output_format(const struct n10_output_handle *h,char *frame,size_t capacity,const char *identity,const char *cycle)
{
    unsigned int reads=!!(h->flags&N10_OUT_FIRST_RETURNED)+!!(h->flags&N10_OUT_LAST_RETURNED);
    int count=snprintf(frame,capacity,
        "id=%s cycle=%s kind=output_scope schema=native-output-scope-v1 flags=%08x reads=%u allocator=vmalloc retained_after_emit=0 lease_cleanup=%s ownership=0 hardware=0 executed=0",
        identity,cycle,h->flags&((1u<<11)-1),reads,(h->flags&N10_OUT_FREE_RETURNED)?"void_returned":"not_called");
    return count>0 && (size_t)count<capacity && count<=447 ? count : 0;
}
static inline int n10_output_zero_format(const struct n10_output_handle *h,char *frame,size_t capacity,const char *identity,const char *cycle)
{
    int count=snprintf(frame,capacity,
        "id=%s cycle=%s kind=prefree_zero schema=native-prefree-output-zero-v1 capacity=%u reads=%u nonzero=%u scan_called=%u scan_returned=%u observed_zero=%u free_called=%u free_returned=%u free_result=%s ownership=0 hardware=0 executed=0",
        identity,cycle,h->bytes,h->scanned,h->nonzero,!!(h->flags&N10_OUT_SCAN_CALLED),!!(h->flags&N10_OUT_SCAN_RETURNED),
        !!(h->flags&N10_OUT_ZERO_OBSERVED),!!(h->flags&N10_OUT_FREE_CALLED),!!(h->flags&N10_OUT_FREE_RETURNED),
        (h->flags&N10_OUT_FREE_RETURNED)?"void_returned":"not_called");
    return count>0 && (size_t)count<capacity && count<=447 ? count : 0;
}
#endif
