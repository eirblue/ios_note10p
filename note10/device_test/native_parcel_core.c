/* SPDX-License-Identifier: GPL-2.0-only */
/* Production bounds/ordering only: no allocation, device access or load call. */
#include "native_parcel_core.h"

static n209_u64 little(const n209_u8 *p, unsigned int bytes)
{
    n209_u64 value = 0; unsigned int i;
    for (i = 0; i < bytes; ++i) value |= (n209_u64)p[i] << (8U*i);
    return value;
}
static int nonzero(const n209_u8 *p, unsigned int bytes)
{
    unsigned int i, bits = 0;
    for (i = 0; i < bytes; ++i) bits |= p[i];
    return bits != 0;
}
static int magic(const n209_u8 *p)
{
    static const char expected[8] = {'N','2','0','9','P','A','Y','1'};
    unsigned int i;
    for (i = 0; i < 8; ++i) if (p[i] != (n209_u8)expected[i]) return 0;
    return 1;
}
int n209_decode_payload(const n209_u8 *wire, unsigned long bytes, struct n209_payload *out)
{
    unsigned int i; n209_u64 scalars[10];
    if (!wire || !out || bytes != N209_PAYLOAD_BYTES || !magic(wire) ||
        little(wire+8,4) != 1 || little(wire+12,4) != N209_PAYLOAD_BYTES) return -22;
    for (i = 0; i < 8; ++i) out->magic[i] = wire[i];
    out->schema = 1; out->bytes = N209_PAYLOAD_BYTES;
    for (i = 0; i < 10; ++i) scalars[i] = little(wire+16+8*i,8);
    out->virtual_base=scalars[0]; out->kernel_span=scalars[1]; out->kernel_entry_offset=scalars[2];
    out->entry_extent_offset=scalars[3]; out->entry_extent_bytes=scalars[4];
    out->pool_offset=scalars[5]; out->pool_bytes=scalars[6]; out->adapter_bytes=scalars[7];
    out->adapter_entry_offset=scalars[8]; out->adapter_record_offset=scalars[9];
    for (i = 0; i < 32; ++i) {
        out->kernel_sha256[i]=wire[96+i]; out->materialized_sha256[i]=wire[128+i];
        out->adapter_sha256[i]=wire[160+i]; out->producer_id[i]=wire[192+i]; out->input_binding[i]=wire[224+i];
    }
    return 0;
}
static int extent(n209_u64 start, n209_u64 bytes, n209_u64 limit)
{ return bytes && start <= limit && bytes <= limit-start; }
int n209_layout_bounds(const struct n209_payload *p, const struct n209_destination *d,
                       n209_u64 adt_bytes, struct n209_layout *out)
{
    struct n209_layout candidate; unsigned int i, build_nonzero = 0;
    if (!p || !d || !out ||
        !magic(p->magic) || p->schema != 1 || p->bytes != N209_PAYLOAD_BYTES ||
        !p->kernel_span || p->kernel_span > N209_DESTINATION_BYTES || p->kernel_span%N209_PAGE ||
        p->virtual_base%N209_PAGE || p->virtual_base > ~(n209_u64)0-N209_DESTINATION_BYTES ||
        !extent(p->entry_extent_offset,p->entry_extent_bytes,p->kernel_span) || p->entry_extent_bytes < 4 ||
        p->kernel_entry_offset%4 || p->kernel_entry_offset < p->entry_extent_offset ||
        p->kernel_entry_offset-p->entry_extent_offset > p->entry_extent_bytes-4 ||
        !extent(p->pool_offset,p->pool_bytes,p->kernel_span) || p->pool_offset%N209_PAGE || p->pool_bytes%N209_PAGE ||
        (p->pool_offset < p->entry_extent_offset+p->entry_extent_bytes && p->entry_extent_offset < p->pool_offset+p->pool_bytes) ||
        p->adapter_bytes != N209_PAGE || p->adapter_entry_offset%4 || p->adapter_entry_offset > N209_PAGE-4 ||
        p->adapter_record_offset%64 || p->adapter_record_offset > N209_PAGE-64 ||
        (p->adapter_entry_offset >= p->adapter_record_offset && p->adapter_entry_offset-p->adapter_record_offset < 64) ||
        !nonzero(p->kernel_sha256,32) || !nonzero(p->materialized_sha256,32) || !nonzero(p->adapter_sha256,32) ||
        !nonzero(p->producer_id,32) || !nonzero(p->input_binding,32) ||
        d->size != N209_DESTINATION_BYTES || d->base < N209_ADDRESS_MIN || d->base > N209_ADDRESS_LIMIT-d->size ||
        d->base%N209_PAGE || d->base%d->size != p->virtual_base%d->size ||
        d->generation != 1 || d->page_shift != 12 || d->status != 1 || !nonzero(d->cookie,16) ||
        !adt_bytes || adt_bytes > N209_ADT_MAX) return -22;
    for (i = 0; i < 32; ++i) {
        if (!((d->build[i]>='0' && d->build[i]<='9') || (d->build[i]>='a' && d->build[i]<='f'))) return -22;
        build_nonzero |= d->build[i] != '0';
    }
    if (!build_nonzero) return -22;
    candidate.args_offset=p->kernel_span;
    if (candidate.args_offset > d->size-N209_PAGE) return -22;
    candidate.adt_offset=candidate.args_offset+N209_PAGE;
    candidate.adt_bytes=adt_bytes;
    if (!extent(candidate.adt_offset,adt_bytes,d->size)) return -22;
    candidate.adapter_offset=(candidate.adt_offset+adt_bytes+N209_PAGE-1)&~(N209_PAGE-1);
    if (!extent(candidate.adapter_offset,N209_PAGE,d->size)) return -22;
    candidate.top_offset=candidate.adapter_offset+N209_PAGE;
    *out=candidate;
    return 0;
}

int n209_prepare_layout(const struct n209_payload *p, const struct n209_destination *d,
                       n209_u64 adt_bytes, const struct n209_prerequisites *ops, void *context,
                       struct n209_layout *out)
{
    struct n209_layout candidate;
    if (!ops || !out || !ops->source_live || !ops->destination_current || !ops->return_qualified ||
        n209_layout_bounds(p,d,adt_bytes,&candidate)) return -22;
    if (ops->source_live(context,p) || ops->destination_current(context,d) || ops->return_qualified(context)) return -5;
    *out=candidate; return 0;
}
