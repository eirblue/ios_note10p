/* SPDX-License-Identifier: GPL-2.0-only */
/* Shared production admission/order core. No allocation, hardware or syscalls. */
#ifdef __KERNEL__
#include <linux/legacy_kexec_core.h>
#else
#include "legacy_kexec_core.h"
#endif
static int n10_equal(const void *a, const void *b, unsigned long n)
{
    const n10_u8 *x=a,*y=b; unsigned long i;
    for(i=0;i<n;i++)if(x[i]!=y[i])return 0;
    return 1;
}
int n10_reserve_destination(const struct n10_reserve_ops *ops, void *context, n10_u64 *out)
{
    n10_u64 base;
    if(!ops || !out || !ops->find || !ops->memory || !ops->reserved || !ops->reserve)return -22;
    base=ops->find(context,N10_KEXEC_MIN,N10_KEXEC_LIMIT,N10_KEXEC_BYTES,N10_KEXEC_ALIGN);
    if(base<N10_KEXEC_MIN || base%N10_KEXEC_ALIGN || base>N10_KEXEC_LIMIT-N10_KEXEC_BYTES ||
       !ops->memory(context,base,N10_KEXEC_BYTES) || ops->reserved(context,base,N10_KEXEC_BYTES))return -22;
    if(ops->reserve(context,base,N10_KEXEC_BYTES))return -12;
    *out=base; return 0;
}
int n10_destination_valid(const struct n10_destination *d, const char *build)
{
    unsigned int i, cookie=0;
    if(!d || !build || !n10_equal(d->magic,"N10KRES1",8) || d->schema!=1 || d->bytes!=sizeof(*d) ||
       d->status!=1 || d->generation!=1 || d->page_shift!=12 || d->size!=N10_KEXEC_BYTES ||
       d->base<N10_KEXEC_MIN || d->base%N10_KEXEC_ALIGN || d->base>N10_KEXEC_LIMIT-d->size ||
       d->reserved_pages!=d->size/4096 || d->valid_pages!=d->reserved_pages || !n10_equal(d->build,build,32))return -22;
    for(i=0;i<32;i++)if(!((build[i]>='0' && build[i]<='9') || (build[i]>='a' && build[i]<='f')))return -22;
    for(i=0;i<16;i++){cookie|=d->cookie[i];if(d->reserved[i])return -22;}
    return cookie ? 0 : -22;
}
long n10_loader_proof(const struct n10_destination *d, const char *build, const void *park, unsigned long count,
                      const struct n10_loader_ops *ops, void *context)
{
    struct n10_kexec_segment segment; long result;
    if(n10_destination_valid(d,build) || !park || count!=N10_KEXEC_ALIGN || !ops ||
       !ops->arm || !ops->load || !ops->reboot || !ops->cancel)return -22;
    segment.buf=park;segment.bufsz=count;segment.mem=(const void *)(__UINTPTR_TYPE__)d->base;segment.memsz=d->size;
    result=ops->arm(context,d);if(result)return result;
    result=ops->load(context,d->base,1,&segment,N10_KEXEC_ARCH);
    if(result){ops->cancel(context,d);return result;}
    result=ops->reboot(context);
    ops->cancel(context,d); /* A successful kernel handoff never returns. No retry. */
    return result ? result : -5;
}
int n10_stage_marker(const struct n10_marker_ops *ops, void *context, n10_u32 mask, n10_u32 normal, n10_u32 recovery)
{
    n10_u32 value, expected;
    if(!ops || !ops->read || !ops->write || !mask || (normal&~mask))return -22;
    if(ops->read(context,0,&value))return -5;
    expected=(value&~mask)|normal;
    if(ops->write(context,0,expected) || ops->read(context,0,&value) || value!=expected)return -5;
    if(ops->write(context,1,recovery) || ops->read(context,1,&value) || value!=recovery)return -5;
    return 0;
}
int n10_watchdog_qualified(const struct n10_wdt_witness *w)
{
    return w && w->present==1 && w->variant_bound==1 && w->enabled==1 && w->reset_enabled==1 &&
        !w->interrupt_only && w->pmu_route_enabled==1 && w->clock_rate && w->data && w->data<=65535 &&
        w->first_count<=w->data && w->last_count && w->last_count<w->first_count &&
        w->effective_timeout>=1 && w->effective_timeout<=30 ? 0 : -5;
}
