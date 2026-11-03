/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_KERNEL_READONLY_SPAN_H
#define N10_KERNEL_READONLY_SPAN_H
#ifndef N10_KRO_SPAN_CLEAR
#error "explicit span-state clearing required"
#endif
#define N10_KRO_SPAN_BUDGET 59768832u
#define N10_KRO_SPAN_BODY_MAX 415u
#define N10_KRO_SPAN_CAPACITY 4440064u
#define N10_KRO_SPAN_DESCRIPTOR_BYTES 80u
enum n10_kro_span_reason {
    N10_KRO_SPAN_UNREACHED=1,N10_KRO_SPAN_KERNEL=2,N10_KRO_SPAN_NULL=4,
    N10_KRO_SPAN_OVERFLOW=8,N10_KRO_SPAN_OUTSIDE=16,N10_KRO_SPAN_OVERLAP=32,N10_KRO_SPAN_BUDGET_ERROR=64,N10_KRO_SPAN_EXTENT=128
};
/* bits: attempted, kernel-valid, slot-contained, descriptor-contained,
 * disjoint, descriptor-admission-called, extents-checked. No stored address. */
struct n10_kro_span { uint64_t kernel_bytes; uint32_t bits,reasons; };
_Static_assert(sizeof(struct n10_kro_span)==16,"exact scalar logical span evidence");
static inline void n10_kro_span_unreached(struct n10_kro_span *out)
{
    N10_KRO_SPAN_CLEAR(out,sizeof(*out));out->reasons=N10_KRO_SPAN_UNREACHED;
}
/* Scalar-only shared precondition; no descriptor/input read or address export. */
static inline int n10_kro_span_check(struct n10_kro_span *out,uintptr_t kernel_start,uintptr_t kernel_end,
    uintptr_t descriptor,size_t descriptor_bytes,uintptr_t slot,size_t capacity)
{
    uintptr_t a=slot,b=descriptor,ae,be;
    N10_KRO_SPAN_CLEAR(out,sizeof(*out));out->bits=1;
    out->reasons=N10_KRO_SPAN_KERNEL;
    if(!kernel_start || kernel_end<=kernel_start) return -1;
    out->reasons=N10_KRO_SPAN_BUDGET_ERROR;
    if(kernel_end-kernel_start>N10_KRO_SPAN_BUDGET) return -1;
    out->kernel_bytes=kernel_end-kernel_start;out->bits|=2;
    out->reasons=N10_KRO_SPAN_NULL;
    if(!a || !b) return -1;
    out->reasons=N10_KRO_SPAN_EXTENT;
    if(capacity!=N10_KRO_SPAN_CAPACITY || descriptor_bytes!=N10_KRO_SPAN_DESCRIPTOR_BYTES) return -1;
    out->reasons=N10_KRO_SPAN_OVERFLOW;
    if(a>UINTPTR_MAX-capacity || b>UINTPTR_MAX-descriptor_bytes) return -1;
    ae=a+capacity;be=b+descriptor_bytes;out->bits|=64;
    if(kernel_start<=a && ae<=kernel_end) out->bits|=4;
    if(kernel_start<=b && be<=kernel_end) out->bits|=8;
    if(ae<=b || be<=a) out->bits|=16;
    out->reasons=0;
    if((out->bits&12)!=12) out->reasons|=N10_KRO_SPAN_OUTSIDE;
    if(!(out->bits&16)) out->reasons|=N10_KRO_SPAN_OVERLAP;
    if(out->reasons) return -1;
    out->bits|=32;
    return 0;
}
#ifndef N10_KRO_SPAN_NO_CLASS2
/* Original class2 adapter stays distinct from the new class3 descriptor ABI. */
static inline int n10_kro_span_admit(struct n10_kro_span *out,uintptr_t kernel_start,uintptr_t kernel_end,
    const struct n10_kro_descriptor *descriptor,size_t descriptor_bytes,const unsigned char *slot,size_t capacity,
    unsigned int source,const unsigned char **input,uint64_t *logical,unsigned char expected[32])
{
    *input=NULL;*logical=0;N10_KRO_SPAN_CLEAR(expected,32);
    if(n10_kro_span_check(out,kernel_start,kernel_end,(uintptr_t)descriptor,descriptor_bytes,(uintptr_t)slot,capacity)) return -1;
    return n10_kro_admit(descriptor,descriptor_bytes,slot,capacity,source,input,logical,expected);
}
#endif
static inline int n10_kro_span_format(const struct n10_kro_span *out,char *frame,size_t capacity,
    const char *identity,const char *cycle)
{
    int count=0;
    const char *slot="na",*descriptor="na",*disjoint="na";
    if(out->bits&64) {
        slot=(out->bits&4) ? "1" : "0";descriptor=(out->bits&8) ? "1" : "0";disjoint=(out->bits&16) ? "1" : "0";
    }
    if(out->bits==127 && !out->reasons && out->kernel_bytes>0 && out->kernel_bytes<=N10_KRO_SPAN_BUDGET) {
        count=snprintf(frame,capacity,
            "id=%s cycle=%s kind=span source=linked-kernel phase=pre_descriptor state=checked attempted=1 kernel_checked=1 kernel_bytes=%llu extents_checked=1 slot_contained=1 descriptor_contained=1 disjoint=1 admission_called=1 reasons=00000000 ownership=0 hardware=0 executed=0",
            identity,cycle,(unsigned long long)out->kernel_bytes);
    } else if(!out->bits && !out->kernel_bytes && out->reasons==N10_KRO_SPAN_UNREACHED) {
        count=snprintf(frame,capacity,
            "id=%s cycle=%s kind=span source=linked-kernel phase=pre_descriptor state=not_reached attempted=0 kernel_checked=0 kernel_bytes=na extents_checked=0 slot_contained=na descriptor_contained=na disjoint=na admission_called=0 reasons=00000001 ownership=0 hardware=0 executed=0",identity,cycle);
    } else if((out->bits&1) && !(out->bits&32) && out->bits<=95 && out->reasons>=2 && out->reasons<=254 && !(out->reasons&1)) {
        if(out->bits&2) {
            count=snprintf(frame,capacity,
                "id=%s cycle=%s kind=span source=linked-kernel phase=pre_descriptor state=refused attempted=1 kernel_checked=1 kernel_bytes=%llu extents_checked=%u slot_contained=%s descriptor_contained=%s disjoint=%s admission_called=0 reasons=%08x ownership=0 hardware=0 executed=0",
                identity,cycle,(unsigned long long)out->kernel_bytes,!!(out->bits&64),slot,descriptor,disjoint,out->reasons);
        } else if(out->bits==1 && !out->kernel_bytes) {
            count=snprintf(frame,capacity,
                "id=%s cycle=%s kind=span source=linked-kernel phase=pre_descriptor state=refused attempted=1 kernel_checked=0 kernel_bytes=na extents_checked=0 slot_contained=na descriptor_contained=na disjoint=na admission_called=0 reasons=%08x ownership=0 hardware=0 executed=0",identity,cycle,out->reasons);
        }
    }
    if(count<1 || (size_t)count>=capacity || (unsigned int)count>N10_KRO_SPAN_BODY_MAX) { N10_KRO_SPAN_CLEAR(frame,capacity);return 0; }
    return count;
}
#endif
