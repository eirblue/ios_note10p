/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_DATA_GROWTH_H
#define N10_DATA_GROWTH_H
#ifndef N10_GROWTH_CLEAR
#error "growth scratch clearing required"
#endif
#define N10_GROWTH_TARGET 59523072u
#define N10_GROWTH_BUDGET 59768832u
#define N10_GROWTH_SOURCE "e32ec501551b74b4cca5618ea25245f012656f29"
#define N10_GROWTH_BODY_MAX 415u
#define N10_GROWTH_QUERIED 16u
/* bits0..3: memory, map-start, reserved, native-initrd-overlap; bit4: queries3. */
struct n10_data_growth { uint32_t current_span, checked, reasons, bits; };
struct n10_growth_temporary {
    uint64_t begin,limit,length,span;
    int memory,map,reserved;
};
_Static_assert(sizeof(struct n10_data_growth)==16,"bounded scalar-only growth state");
_Static_assert(sizeof(struct n10_growth_temporary)==48,"exact cleared temporary growth bounds");
enum n10_growth_reason {
    N10_GROWTH_UNREACHED=1,N10_GROWTH_CAPTURE=2,N10_GROWTH_RANGE=4,
    N10_GROWTH_STABLE=8,N10_GROWTH_TARGET_INVALID=16,N10_GROWTH_QUERY=32,N10_GROWTH_REPEAT=64
};
static inline void n10_growth_unavailable(struct n10_data_growth *out,unsigned int reason)
{
    N10_GROWTH_CLEAR(out,sizeof(*out)); out->reasons=reason;
}
static inline void n10_growth_snapshot(struct n10_data_growth *out,const struct n10_data_growth *saved)
{
    *out=*saved;
    if(!out->checked && !out->reasons) n10_growth_unavailable(out,N10_GROWTH_UNREACHED);
}
/* Existing validated scalar range only. No supplied address is dereferenced. */
static inline void n10_growth_observe(struct n10_data_growth *out,const struct n10_data_range *range,
    unsigned int captures,int stable)
{
    struct n10_growth_temporary tmp={0};
    n10_growth_unavailable(out,N10_GROWTH_CAPTURE);
    if(captures!=1) { out->reasons=captures>1 ? N10_GROWTH_REPEAT : N10_GROWTH_UNREACHED; goto done; }
    out->reasons=N10_GROWTH_STABLE;
    if(stable!=1) goto done;
    out->reasons=N10_GROWTH_RANGE;
    if(range->checked!=1 || range->reasons || range->kernel_end<=range->kernel_start ||
        range->input_end<=range->input_start) goto done;
    tmp.span=range->kernel_end-range->kernel_start;
    out->reasons=N10_GROWTH_TARGET_INVALID;
    if(!tmp.span || tmp.span>=N10_GROWTH_TARGET || N10_GROWTH_TARGET>N10_GROWTH_BUDGET ||
        N10_GROWTH_BUDGET>67108864u || range->kernel_start>UINT64_MAX-N10_GROWTH_BUDGET) goto done;
    tmp.begin=range->kernel_end; tmp.limit=range->kernel_start+N10_GROWTH_BUDGET;
    if(tmp.limit<=tmp.begin) goto done;
    tmp.length=tmp.limit-tmp.begin;
    /* Independent read-only bookkeeping observations. No memory probe or mutation. */
    tmp.memory=N10_GROWTH_MEMORY(tmp.begin,tmp.length);
    tmp.map=N10_GROWTH_MAP(tmp.begin);
    tmp.reserved=N10_GROWTH_RESERVED(tmp.begin,tmp.length);
    out->bits=N10_GROWTH_QUERIED; out->reasons=N10_GROWTH_QUERY;
    if(tmp.memory<0 || tmp.memory>1 || tmp.map<0 || tmp.map>1 || tmp.reserved<0 || tmp.reserved>1) goto done;
    out->bits|=(unsigned int)tmp.memory | ((unsigned int)tmp.map<<1) | ((unsigned int)tmp.reserved<<2) |
        ((unsigned int)(range->input_start<tmp.limit && tmp.begin<range->input_end)<<3);
    out->current_span=(uint32_t)tmp.span; out->checked=1; out->reasons=0;
done:
    N10_GROWTH_CLEAR(&tmp,sizeof(tmp));
}
static inline int n10_growth_format(const struct n10_data_growth *out,char *frame,size_t capacity,
    const char *identity,const char *cycle,unsigned int captures)
{
    int count=0;
    unsigned int queried=(out->bits&N10_GROWTH_QUERIED) ? 3 : 0;
    if(out->checked==1 && !out->reasons && captures==1 && queried==3 && out->bits<=31 &&
        out->current_span>0 && out->current_span<N10_GROWTH_TARGET) {
        count=snprintf(frame,capacity,
            "id=%s cycle=%s kind=growth source=memblock-bookkeeping stage=post_paging captures=1 state=checked current=%u target=%u budget=%u proposal=%s queries=3 memory=%u map_start=%u reserved=%u initrd_overlap=%u reasons=00000000 ownership=0 executed=0",
            identity,cycle,out->current_span,N10_GROWTH_TARGET,N10_GROWTH_BUDGET,N10_GROWTH_SOURCE,
            out->bits&1,(out->bits>>1)&1,(out->bits>>2)&1,(out->bits>>3)&1);
    } else if(!out->checked && !out->current_span && (out->bits==0 || out->bits==N10_GROWTH_QUERIED) &&
        ((captures==0 && out->reasons==N10_GROWTH_UNREACHED && !queried) ||
         (captures==2 && out->reasons==N10_GROWTH_REPEAT && !queried) ||
         (captures==1 && ((!queried && (out->reasons==N10_GROWTH_CAPTURE || out->reasons==N10_GROWTH_RANGE ||
            out->reasons==N10_GROWTH_STABLE || out->reasons==N10_GROWTH_TARGET_INVALID)) ||
            (queried==3 && (out->reasons==N10_GROWTH_STABLE || out->reasons==N10_GROWTH_QUERY)))))) {
        count=snprintf(frame,capacity,
            "id=%s cycle=%s kind=growth source=memblock-bookkeeping stage=post_paging captures=%u state=unavailable current=na target=%u budget=%u proposal=%s queries=%u memory=na map_start=na reserved=na initrd_overlap=na reasons=%08x ownership=0 executed=0",
            identity,cycle,captures,N10_GROWTH_TARGET,N10_GROWTH_BUDGET,N10_GROWTH_SOURCE,queried,out->reasons);
    }
    if(count<1 || (size_t)count>=capacity || (unsigned int)count>N10_GROWTH_BODY_MAX) {
        N10_GROWTH_CLEAR(frame,capacity); return 0;
    }
    return count;
}
#endif
