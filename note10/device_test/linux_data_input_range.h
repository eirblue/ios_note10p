/* SPDX-License-Identifier: GPL-2.0-only */
/* Pinned ARM64 nodebug scalars; never dereference a supplied input/kernel address. */
#ifndef N10_DATA_INPUT_RANGE_H
#define N10_DATA_INPUT_RANGE_H
#ifndef N10_RANGE_CLEAR
#error "explicit range scratch clearing required"
#endif
#define N10_RANGE_BODY_MAX 383u
enum n10_range_reason {
    N10_RANGE_UNREACHED=1, N10_RANGE_UNSUPPORTED=2, N10_RANGE_DOMAIN=4,
    N10_RANGE_BOUNDS=8, N10_RANGE_BASE=16, N10_RANGE_OVERFLOW=32,
    N10_RANGE_TRANSLATION=64
};
struct n10_data_range {
    uint64_t input_start, input_end, kernel_start, kernel_end;
    unsigned int checked, reasons, logical_overlap, native_overlap;
};
struct n10_range_input {
    uint64_t start, end, native, logical, text, image_end;
    uint64_t base, offset, page_offset, linear_bit, base_after, offset_after;
    unsigned int supported;
};
_Static_assert(sizeof(struct n10_data_range)==48, "exact private range record");
_Static_assert(sizeof(struct n10_range_input)==104, "exact scalar conversion snapshot");

static inline void n10_range_clear(struct n10_data_range *out)
{
    N10_RANGE_CLEAR(out,sizeof(*out));
}
static inline void n10_range_unavailable(struct n10_data_range *out, unsigned int reason)
{
    n10_range_clear(out); out->reasons=reason;
}

static inline void n10_range_evaluate(const struct n10_range_input *in, struct n10_data_range *out)
{
    uint64_t first, last, input_end, logical_end, kernel_first, kernel_last, kernel_end;
    uint64_t offset_first, offset_last;
    n10_range_unavailable(out,N10_RANGE_UNSUPPORTED);
    if (in->supported!=1 || !in->linear_bit || (in->linear_bit&(in->linear_bit-1)) ||
        in->page_offset!=UINT64_MAX-in->linear_bit+1) return;
    out->reasons=N10_RANGE_BASE;
    if (in->base>(UINT64_MAX>>1) || (in->base&1) || !in->offset ||
        in->base!=in->base_after || in->offset!=in->offset_after) return;
    out->reasons=N10_RANGE_BOUNDS;
    if (!in->start || in->end<=in->start || in->native!=in->end-in->start ||
        in->native<=128 || in->native>67108864 || in->logical<128 || in->logical>in->native ||
        !in->text || in->image_end<=in->text) return;
    out->reasons=N10_RANGE_DOMAIN;
    /* __is_lm_address(x): !!(x & BIT(VA_BITS-1)). */
    if (!(in->start&in->linear_bit) || !((in->end-1)&in->linear_bit) ||
        (in->text&in->linear_bit) || ((in->image_end-1)&in->linear_bit)) return;
    offset_first=in->start&~in->page_offset;
    offset_last=(in->end-1)&~in->page_offset;
    out->reasons=N10_RANGE_OVERFLOW;
    /* __lm_to_phys(x): (x & ~PAGE_OFFSET) + PHYS_OFFSET. */
    if (offset_first>UINT64_MAX-in->base || offset_last>UINT64_MAX-in->base) return;
    first=offset_first+in->base; last=offset_last+in->base;
    if (first>UINT64_MAX-in->native || first>UINT64_MAX-in->logical ||
        in->text<in->offset || in->image_end-1<in->offset) return;
    input_end=first+in->native; logical_end=first+in->logical;
    /* __pa_symbol_nodebug(x): (phys_addr_t)x - kimage_voffset. */
    kernel_first=in->text-in->offset; kernel_last=in->image_end-1-in->offset;
    if (kernel_last==UINT64_MAX || kernel_first>UINT64_MAX-in->offset ||
        kernel_last>UINT64_MAX-in->offset) return;
    kernel_end=kernel_last+1;
    out->reasons=N10_RANGE_TRANSLATION;
    if (last!=input_end-1 || kernel_end<=kernel_first ||
        kernel_end-kernel_first!=in->image_end-in->text ||
        (((first-in->base)|in->page_offset)!=in->start) ||
        (((last-in->base)|in->page_offset)!=in->end-1) ||
        kernel_first+in->offset!=in->text || kernel_last+in->offset!=in->image_end-1) return;
    out->input_start=first; out->input_end=input_end;
    out->kernel_start=kernel_first; out->kernel_end=kernel_end;
    out->logical_overlap=first<kernel_end && kernel_first<logical_end;
    out->native_overlap=first<kernel_end && kernel_first<input_end;
    out->reasons=0; out->checked=1;
}

static inline int n10_range_format(const struct n10_data_range *out, char *frame, size_t capacity,
    const char *identity, const char *cycle, unsigned long long logical)
{
    int count;
    if (out->checked==1 && !out->reasons && out->logical_overlap<=1 && out->native_overlap<=1 &&
        (!out->logical_overlap || out->native_overlap)) {
        count=snprintf(frame,capacity,
            "id=%s cycle=%s kind=range source=live-arm64 extent=native state=checked domain=physical logical=%llu input_start=%016llx input_end=%016llx kernel_start=%016llx kernel_end=%016llx logical_overlap=%u native_overlap=%u reasons=00000000 ownership=0 executed=0",
            identity,cycle,logical,(unsigned long long)out->input_start,(unsigned long long)out->input_end,
            (unsigned long long)out->kernel_start,(unsigned long long)out->kernel_end,
            out->logical_overlap,out->native_overlap);
    } else if (!out->checked && out->reasons && out->reasons<=127) {
        count=snprintf(frame,capacity,
            "id=%s cycle=%s kind=range source=live-arm64 extent=native state=unavailable domain=none logical=%llu input_start=na input_end=na kernel_start=na kernel_end=na logical_overlap=na native_overlap=na reasons=%08x ownership=0 executed=0",
            identity,cycle,logical,out->reasons);
    } else count=0;
    if (count<1 || (size_t)count>=capacity || (unsigned int)count>N10_RANGE_BODY_MAX) {
        N10_RANGE_CLEAR(frame,capacity); return 0;
    }
    return count;
}
#endif
