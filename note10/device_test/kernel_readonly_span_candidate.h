/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_KERNEL_READONLY_SPAN_CANDIDATE_H
#define N10_KERNEL_READONLY_SPAN_CANDIDATE_H
#include "carrier_lzma.h"
#define N10_KRO3_CAPACITY 4440064u
#define N10_KRO3_ALIGN 16u
#define N10_KRO3_DESCRIPTOR_BYTES 80u
#define N10_KRO3_SOURCE 3u
#define N10_KRO3_MAGIC "N10KROINPUTV3!!!"
struct n10_kro3_descriptor {
    unsigned char magic[16], version[4], bytes[4], capacity[8], logical[8], expected[32], reserved[8];
};
_Static_assert(sizeof(struct n10_kro3_descriptor)==80,"closed readonly descriptor");
static uint64_t n10_kro3_le(const unsigned char *p,unsigned int n)
{
    uint64_t value=0;
    unsigned int i;
    for(i=0;i<n;++i) value|=(uint64_t)READ_ONCE(p[i])<<(8*i);
    return value;
}
/* Descriptor reads only. No input byte access or physical ownership claim. */
static int n10_kro3_admit(const struct n10_kro3_descriptor *d,size_t descriptor_bytes,
    const unsigned char *slot,size_t capacity,unsigned int source,
    const unsigned char **input,uint64_t *logical,unsigned char expected[32])
{
    unsigned int i,any=0;
    uint64_t length;
    *input=NULL; *logical=0;
    memset(expected,0,32);
    if(!d || !slot || source!=N10_KRO3_SOURCE || descriptor_bytes!=80 ||
        capacity!=N10_KRO3_CAPACITY || ((uintptr_t)slot & (N10_KRO3_ALIGN-1)) ||
        (uintptr_t)slot>UINTPTR_MAX-capacity) return -1;
    for(i=0;i<16;++i) if(READ_ONCE(d->magic[i])!=(unsigned char)N10_KRO3_MAGIC[i]) return -1;
    if(n10_kro3_le(d->version,4)!=3 || n10_kro3_le(d->bytes,4)!=80 ||
        n10_kro3_le(d->capacity,8)!=N10_KRO3_CAPACITY) return -1;
    for(i=0;i<8;++i) if(READ_ONCE(d->reserved[i])) return -1;
    length=n10_kro3_le(d->logical,8);
    for(i=0;i<32;++i) any|=READ_ONCE(d->expected[i]);
    if(!any && !length) return 0;
    if(!any || length!=N10_KRO3_CAPACITY) return -1;
    for(i=0;i<32;++i) expected[i]=READ_ONCE(d->expected[i]);
    *logical=length; *input=slot;
    return 1;
}
#define N10_KRO_SPAN_NO_CLASS2 1
#include "kernel_readonly_span.h"
#undef N10_KRO_SPAN_NO_CLASS2
/* Type3 only, after the unchanged scalar complete-range precondition. */
static inline int n10_kro3_span_admit(struct n10_kro_span *out,uintptr_t kernel_start,uintptr_t kernel_end,
    const struct n10_kro3_descriptor *descriptor,size_t descriptor_bytes,const unsigned char *slot,size_t capacity,
    unsigned int source,const unsigned char **input,uint64_t *logical,unsigned char expected[32])
{
    *input=NULL;*logical=0;N10_KRO_SPAN_CLEAR(expected,32);
    if(n10_kro_span_check(out,kernel_start,kernel_end,(uintptr_t)descriptor,descriptor_bytes,(uintptr_t)slot,capacity)) return -1;
    return n10_kro3_admit(descriptor,descriptor_bytes,slot,capacity,source,input,logical,expected);
}
#endif
