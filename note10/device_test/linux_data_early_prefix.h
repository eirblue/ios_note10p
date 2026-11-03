/* SPDX-License-Identifier: GPL-2.0-only */
/* One early prefix sample, only after the capture and RAM/map phase guards. */
#ifndef N10_DATA_EARLY_PREFIX_H
#define N10_DATA_EARLY_PREFIX_H
#if !defined(N10_EARLY_CLEAR) || !defined(N10_EARLY_COPY8)
#error "explicit early read/clear boundary required"
#endif
#define N10_EARLY_BODY_MAX 255u
enum n10_early_reason {
    N10_EARLY_NOT_REACHED=1, N10_EARLY_CAPTURE_INVALID=2, N10_EARLY_REPEAT=4,
    N10_EARLY_GLOBAL=8, N10_EARLY_RAM=16
};
struct n10_early_prefix {
    unsigned int sampled, magic_match, prefix_zero, reasons;
};
_Static_assert(sizeof(struct n10_early_prefix)==16,"exact permanent early flags only");
static inline void n10_early_clear(struct n10_early_prefix *out)
{
    N10_EARLY_CLEAR(out,sizeof(*out));
}
static inline void n10_early_unavailable(struct n10_early_prefix *out,unsigned int reason)
{
    n10_early_clear(out); out->reasons=reason;
}
static inline void n10_early_snapshot(struct n10_early_prefix *out,const struct n10_early_prefix *saved)
{
    *out=*saved;
    if(!out->sampled && !out->reasons) n10_early_unavailable(out,N10_EARLY_NOT_REACHED);
}
static inline void n10_early_observe(struct n10_early_prefix *out,const unsigned char *input,
    unsigned int captures,unsigned int same_globals,unsigned int ram_and_map)
{
    unsigned char prefix[8];
    unsigned int i,any=0;
    if(captures!=1 || out->sampled || out->reasons==N10_EARLY_REPEAT) {
        n10_early_unavailable(out,N10_EARLY_REPEAT); return;
    }
    if(same_globals!=1) { n10_early_unavailable(out,N10_EARLY_GLOBAL); return; }
    if(ram_and_map!=1) { n10_early_unavailable(out,N10_EARLY_RAM); return; }
    N10_EARLY_COPY8(prefix,input);
    for(i=0;i<sizeof(prefix);++i) any|=prefix[i];
    out->magic_match=memcmp(prefix,"N10DATA1",sizeof(prefix))==0;
    out->prefix_zero=!any; out->sampled=1; out->reasons=0;
    N10_EARLY_CLEAR(prefix,sizeof(prefix));
}
static inline int n10_early_format(const struct n10_early_prefix *out,char *frame,size_t capacity,
    const char *identity,const char *cycle,unsigned int captures)
{
    int count=0;
    if(captures<=2 && ((out->sampled==1 && !out->reasons && captures==1 &&
        out->magic_match<=1 && out->prefix_zero<=1 && !(out->magic_match&&out->prefix_zero)) ||
        (!out->sampled && out->reasons && out->reasons<=31 && !out->magic_match && !out->prefix_zero))) {
        count=snprintf(frame,capacity,
            "id=%s cycle=%s kind=early source=memblock-ram-map phase=post_paging state=%s captures=%u sampled=%u magic_match=%s prefix_zero=%s reasons=%08x ownership=0 executed=0",
            identity,cycle,out->sampled ? "sampled" : "unavailable",captures,out->sampled,
            out->sampled ? (out->magic_match ? "1" : "0") : "na",
            out->sampled ? (out->prefix_zero ? "1" : "0") : "na",out->reasons);
    }
    if(count<1 || (size_t)count>=capacity || (unsigned int)count>N10_EARLY_BODY_MAX) {
        N10_EARLY_CLEAR(frame,capacity); return 0;
    }
    return count;
}
#endif
