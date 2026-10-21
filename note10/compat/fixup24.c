#include "fixup24.h"

int n10_decode_fixup24(uint64_t raw, struct n10_fixup24 *out)
{
    if (!out)
        return 0;
    struct n10_fixup24 d = {0};
    d.authenticated = (uint8_t)(raw >> 63);
    d.bind = (uint8_t)((raw >> 62) & 1);
    d.next_bytes = (uint16_t)(((raw >> 51) & 0x7ff) * 8);
    if (d.bind) {
        if ((raw >> 24) & 0xff) /* Reserved zero field, not ordinal bits. */
            return 0;
        d.ordinal = (uint32_t)(raw & 0xffffff);
    }
    if (d.authenticated) {
        if (!d.bind)
            d.target = raw & 0xffffffff;
        d.diversity = (uint16_t)(raw >> 32);
        d.address_diversity = (uint8_t)((raw >> 48) & 1);
        d.key = (uint8_t)((raw >> 49) & 3); /* IA, IB, DA, DB. */
    } else if (d.bind) {
        uint32_t encoded = (uint32_t)((raw >> 32) & 0x7ffff);
        d.addend = encoded < 0x40000 ? (int32_t)encoded : (int32_t)encoded - 0x80000;
    } else {
        d.target = raw & 0x7ffffffffffULL;
        d.high8 = (uint8_t)((raw >> 43) & 0xff);
    }
    *out = d;
    return 1;
}

enum n10_walk24_result n10_walk_fixup24_page(const uint8_t *page, size_t size,
                                           uint16_t start, n10_visit_fixup24 visit,
                                           void *context)
{
    if (!page || !visit || (size != 4096 && size != 16384))
        return N10_WALK24_BAD_INPUT;
    if (start == 0xffff) /* DYLD_CHAINED_PTR_START_NONE */
        return N10_WALK24_OK;
    if (start & 0x8000) /* MULTI is deliberately unsupported here. */
        return N10_WALK24_BAD_INPUT;
    size_t offset = start;
    for (;;) {
        if (offset > size - 8)
            return N10_WALK24_BOUNDS;
        uint64_t raw = 0;
        for (unsigned i = 0; i < 8; ++i)
            raw |= (uint64_t)page[offset + i] << (i * 8);
        struct n10_fixup24 d;
        if (!n10_decode_fixup24(raw, &d))
            return N10_WALK24_ENCODING;
        if (visit(context, offset, raw, &d) != 1)
            return N10_WALK24_VISITOR_STOPPED;
        if (!d.next_bytes)
            return N10_WALK24_OK;
        /* next_bytes is positive and bounded, so cycles/size_t wrap cannot occur. */
        offset += d.next_bytes;
    }
}
