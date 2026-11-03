/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_NATIVE_SCOPED_OUTPUT_H
#define N10_NATIVE_SCOPED_OUTPUT_H
#include "carrier_lzma.h"
/* Native caller-local scope only: no global storage, asynchronous retention,
 * physical address translation, allocation or transferable security token. */
struct n10_output_handle { unsigned char *data; size_t bytes; uint32_t flags; };
_Static_assert(sizeof(struct n10_output_handle)==24,"native scoped output handle24");
enum { N10_OUT_OFFERED=1u<<0,N10_OUT_BORROWED=1u<<1,N10_OUT_FIRST_RETURNED=1u<<2,
    N10_OUT_LAST_RETURNED=1u<<3,N10_OUT_RELEASED=1u<<4,N10_OUT_RETIRED=1u<<5,
    N10_OUT_CLEAR_CALLED=1u<<6,N10_OUT_CLEAR_RETURNED=1u<<7,N10_OUT_FREE_CALLED=1u<<8,
    N10_OUT_FREE_RETURNED=1u<<9,N10_OUT_REFUSED=1u<<10 };
#define N10_OUT_ALL ((1u<<10)-1)
#ifndef N10_OUTPUT_READ_ONCE
#define N10_OUTPUT_READ_ONCE(x) READ_ONCE(x)
#endif
static inline int n10_output_offer(struct n10_output_handle *h,unsigned char *data,size_t bytes)
{
    if(!h || h->data || h->bytes || h->flags || !data || !bytes || bytes>N10_LZMA_MAX_BYTES ||
        (uintptr_t)data>UINTPTR_MAX-bytes) return -1;
    h->data=data;h->bytes=bytes;h->flags=N10_OUT_OFFERED;
    return 0;
}
static inline int n10_output_read_and_release(struct n10_output_handle *h)
{
    const unsigned char *p;
    if(!h || h->flags!=N10_OUT_OFFERED || !h->data || !h->bytes || h->bytes>N10_LZMA_MAX_BYTES ||
        (uintptr_t)h->data>UINTPTR_MAX-h->bytes) {
        if(h) h->flags|=N10_OUT_REFUSED;
        return -1;
    }
    p=h->data;h->flags|=N10_OUT_BORROWED;
    (void)N10_OUTPUT_READ_ONCE(p[0]);h->flags|=N10_OUT_FIRST_RETURNED;
    (void)N10_OUTPUT_READ_ONCE(p[h->bytes-1]);h->flags|=N10_OUT_LAST_RETURNED;
    h->flags|=N10_OUT_RELEASED;
    return 0;
}
static inline int n10_output_format(const struct n10_output_handle *h,char *frame,size_t capacity,
    const char *identity,const char *cycle)
{
    unsigned int reads=!!(h->flags&N10_OUT_FIRST_RETURNED)+!!(h->flags&N10_OUT_LAST_RETURNED);
    int count=snprintf(frame,capacity,
        "id=%s cycle=%s kind=output_scope schema=native-output-scope-v1 flags=%08x reads=%u allocator=vmalloc retained_after_emit=0 lease_cleanup=%s ownership=0 hardware=0 executed=0",
        identity,cycle,h->flags,reads,(h->flags&N10_OUT_FREE_RETURNED)?"void_returned":"not_called");
    if(count<1 || (size_t)count>=capacity || count>447) return 0;
    return count;
}
#endif
