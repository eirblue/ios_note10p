/* SPDX-License-Identifier: GPL-2.0-only */
/* NEW pure scalar conversion/interval fixture. All coordinates are invented. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#define N10_RANGE_CLEAR(p,n) memset((p),0,(n))
#include "linux_data_input_range.h"
#undef N10_RANGE_CLEAR

static unsigned int zeroed(const void *p,size_t size)
{
    size_t i;
    for(i=0;i<size;++i) if(((const unsigned char *)p)[i]) return 0;
    return 1;
}
static uint32_t checksum(const char *body,int count)
{
    uint32_t value=2166136261U;
    int i;
    for(i=0;i<count;++i) value=(value^(unsigned char)body[i])*16777619U;
    return value;
}
static struct n10_range_input sample(void)
{
    struct n10_range_input in={0};
    in.linear_bit=UINT64_C(1)<<63; in.page_offset=in.linear_bit;
    in.start=in.page_offset+0x2000; in.end=in.start+4096;
    in.native=4096; in.logical=3000; in.base=0x1000; in.base_after=in.base;
    in.offset=0x100000; in.offset_after=in.offset;
    in.text=in.offset+0x3400; in.image_end=in.text+4096; in.supported=1;
    return in;
}
static int one(const char *name,struct n10_range_input in,unsigned int first)
{
    struct n10_data_range out;
    char body[448];
    unsigned int checked,reasons,cleared,snapshot_clear;
    uint64_t span;
    int count;
    if(in.supported==2) n10_range_unavailable(&out,N10_RANGE_UNREACHED);
    else n10_range_evaluate(&in,&out);
    checked=out.checked; reasons=out.reasons;
    span=checked ? out.kernel_end-out.kernel_start : 4096;
    count=n10_range_format(&out,body,sizeof(body),"11111111111111111111111111111111",
        "22222222222222222222222222222222",(unsigned long long)in.logical);
    n10_range_clear(&out); cleared=zeroed(&out,sizeof(out));
    if(!count || !cleared) return 0;
    printf("%s{\"name\":\"%s\",\"checked\":%u,\"reasons\":%u,\"native\":%llu,\"logical\":%llu,\"kernel_span\":%llu,\"length\":%d,\"cleared\":%u,\"frame\":\"N10BOOTLINK2 boot=33333333333333333333333333333333 N10DATARANGE1 %s checksum=%08x\"}",
        first ? "" : ",",name,checked,reasons,(unsigned long long)in.native,
        (unsigned long long)in.logical,(unsigned long long)span,count,cleared,body,checksum(body,count));
    memset(&in,0,sizeof(in)); snapshot_clear=zeroed(&in,sizeof(in));
    memset(body,0,sizeof(body));
    return snapshot_clear;
}
int main(void)
{
    struct n10_range_input in;
    struct n10_data_range out;
    struct { unsigned char before[8]; char body[8]; unsigned char after[8]; } guard;
    char invalid_body[448];
    unsigned int i,short_ok,invalid_rejected;
    int count;
    printf("{\"range_bytes\":%zu,\"snapshot_bytes\":%zu,\"body_cap\":%u,\"frame_capacity\":448,\"cases\":[",
        sizeof(out),sizeof(in),N10_RANGE_BODY_MAX);
    in=sample(); if(!one("logical_overlap",in,1)) return 1;
    in=sample(); in.text=in.offset+0x8000; in.image_end=in.text+4096;
    if(!one("disjoint",in,0)) return 1;
    in=sample(); in.text=in.offset+0x4000; in.image_end=in.text+4096;
    if(!one("touching",in,0)) return 1;
    in=sample(); in.text=in.offset+0x3c00; in.image_end=in.text+4096;
    if(!one("tail_only",in,0)) return 1;
    in=sample(); in.text=in.offset+0x2000; in.image_end=in.offset+0x5000;
    if(!one("contained",in,0)) return 1;
    in=sample(); in.native=in.logical=67108864; in.end=in.start+in.native;
    if(!one("maximum_count",in,0)) return 1;
    in=sample(); in.start=0x2000; in.end=in.start+in.native;
    if(!one("mixed_domain",in,0)) return 1;
    in=sample(); in.base_after+=2; if(!one("unstable_base",in,0)) return 1;
    in=sample(); in.base=in.base_after=UINT64_MAX;
    if(!one("uninitialized_base",in,0)) return 1;
    in=sample(); in.offset=in.offset_after=in.text+1;
    if(!one("symbol_subtraction_underflow",in,0)) return 1;
    in=sample(); in.start=UINT64_MAX-63; in.end=32;
    if(!one("virtual_end_wrap",in,0)) return 1;
    in=sample(); in.supported=0; if(!one("unsupported_debug",in,0)) return 1;
    in=sample(); in.page_offset=0; if(!one("wrong_mask",in,0)) return 1;
    in=sample(); in.supported=2; if(!one("not_reached",in,0)) return 1;
    in=sample(); n10_range_evaluate(&in,&out); memset(&guard,0xa5,sizeof(guard));
    count=n10_range_format(&out,guard.body,sizeof(guard.body),"11111111111111111111111111111111",
        "22222222222222222222222222222222",3000);
    short_ok=!count && zeroed(guard.body,sizeof(guard.body));
    for(i=0;i<8;++i) if(guard.before[i]!=0xa5 || guard.after[i]!=0xa5) short_ok=0;
    n10_range_clear(&out); memset(&in,0,sizeof(in));
    memset(invalid_body,0xa5,sizeof(invalid_body));
    count=n10_range_format(&out,invalid_body,sizeof(invalid_body),
        "11111111111111111111111111111111","22222222222222222222222222222222",3000);
    invalid_rejected=!count && zeroed(invalid_body,sizeof(invalid_body));
    printf("],\"short_buffer_rejected\":%u,\"zero_reason_unavailable_rejected\":%u,\"input_byte_reads\":0,\"hash_calls\":0,\"decoder_calls\":0}\n",short_ok,invalid_rejected);
    return short_ok && invalid_rejected ? 0 : 1;
}
