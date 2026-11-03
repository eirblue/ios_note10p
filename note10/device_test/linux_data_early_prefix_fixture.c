/* SPDX-License-Identifier: GPL-2.0-only */
/* NEW actual capture boundary with mocked address/RAM metadata; no decoder. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
static unsigned char bytes[8];
static unsigned long initrd_start,initrd_end,host_first,host_end;
static unsigned int reads,read_bytes,scratch_clears,clear_failed,ram_calls,map_calls,span_ok,map_arg_ok;
static int ram_result,map_result,bad_linear,bad_roundtrip,overflow_pa,change_after_map;
static void fixture_clear(void *p,size_t n)
{
    size_t i;
    memset(p,0,n);
    if(n==8) { ++scratch_clears; for(i=0;i<n;++i) if(((unsigned char *)p)[i]) clear_failed=1; }
}
static void fixture_copy8(void *out,const void *in)
{
    ++reads; read_bytes+=8; memcpy(out,in,8);
}
static uint64_t fixture_pa(unsigned long address)
{
    return overflow_pa ? UINT64_MAX-16 : 0x10000+(uint64_t)(address-host_first);
}
static unsigned long fixture_va(uint64_t physical)
{
    return host_first+(unsigned long)(physical-0x10000)+(bad_roundtrip ? 1 : 0);
}
static int fixture_ram(uint64_t base,size_t length)
{
    ++ram_calls; span_ok=base==0x10000 && length==4096; return ram_result;
}
static int fixture_map(uint64_t base)
{
    ++map_calls; map_arg_ok=base==0x10000;
    if(change_after_map) ++initrd_end;
    return map_result;
}
#define N10_DATA_HOST_TEST 1
#define N10_DATA_IMAGE_EXPECTATION 1
#define N10_DATA_EARLY_EVIDENCE 1
#define N10_DATA_EARLY_CAPTURE_ONLY 1
#define __init
#define __used __attribute__((used))
#define READ_ONCE(x) (*(volatile __typeof__(x) *)&(x))
#define n10_data_linear(x) (!bad_linear && (x)>=host_first && (x)<host_end)
#define n10_data_pa(x) fixture_pa(x)
#define n10_data_va(x) fixture_va(x)
#define n10_data_clear(p,n) fixture_clear((p),(n))
#define n10_data_region_memory(p,n) fixture_ram((p),(n))
#define n10_data_map_memory(p) fixture_map(p)
#define N10_EARLY_COPY8(p,s) fixture_copy8((p),(s))
#include "linux_data_carrier.c"

static uint32_t checksum(const char *body,int count)
{
    uint32_t value=2166136261U;
    int i;
    for(i=0;i<count;++i) value=(value^(unsigned char)body[i])*16777619U;
    return value;
}
static unsigned int zeroed(const void *p,size_t n)
{
    size_t i;
    for(i=0;i<n;++i) if(((const unsigned char *)p)[i]) return 0;
    return 1;
}
static void reset(void)
{
    memset(&n10_data,0,sizeof(n10_data));
    memcpy(bytes,"N10DATA1",8);
    host_first=(unsigned long)bytes; host_end=host_first+4096;
    initrd_start=host_first; initrd_end=host_end;
    reads=read_bytes=scratch_clears=clear_failed=ram_calls=map_calls=span_ok=map_arg_ok=0;
    ram_result=map_result=1; bad_linear=bad_roundtrip=overflow_pa=change_after_map=0;
}
static int one(const char *name,unsigned int mode,unsigned int first)
{
    struct n10_early_prefix out;
    char body[448];
    unsigned int captures,cleared;
    int count;
    reset();
    if(mode==1) memset(bytes,0,8);
    if(mode==2) memcpy(bytes,"OTHER123",8);
    if(mode==3) ram_result=0;
    if(mode==4) map_result=0;
    if(mode==5) bad_linear=1;
    if(mode==6) bad_roundtrip=1;
    if(mode==7) overflow_pa=1;
    if(mode==8) ++initrd_start;
    if(mode==9) change_after_map=1;
    if(mode==10) ram_result=-1;
    if(mode!=11) {
        if(mode==13) n10_data_capture(0,host_end);
        else n10_data_capture(host_first,host_end);
    }
    if(mode==12 || mode==13) n10_data_capture(host_first,host_end);
    captures=n10_data.captures>1 ? 2 : n10_data.captures;
    n10_early_snapshot(&out,&n10_data.early);
    count=n10_early_format(&out,body,sizeof(body),"11111111111111111111111111111111",
        "22222222222222222222222222222222",captures);
    n10_early_clear(&out); cleared=zeroed(&out,sizeof(out));
    if(!count || !cleared || clear_failed || reads>1) return 0;
    printf("%s{\"name\":\"%s\",\"captures\":%u,\"reads\":%u,\"read_bytes\":%u,\"scratch_clears\":%u,\"ram_queries\":%u,\"map_queries\":%u,\"full_span_argument_ok\":%u,\"map_argument_ok\":%u,\"cleared\":%u,\"length\":%d,\"frame\":\"N10BOOTLINK2 boot=33333333333333333333333333333333 N10DATAEARLY1 %s checksum=%08x\"}",
        first ? "" : ",",name,captures,reads,read_bytes,scratch_clears,ram_calls,map_calls,span_ok,map_arg_ok,cleared,count,body,checksum(body,count));
    memset(body,0,sizeof(body)); return 1;
}
int main(void)
{
    struct n10_early_prefix out={0};
    struct { unsigned char left[8]; char body[8]; unsigned char right[8]; } guard;
    char body[448];
    unsigned int i,short_ok,invalid_ok;
    int count;
    const char *names[]={"magic","zero","other","not_ram","nomap","nonlinear","roundtrip","overflow",
        "globals_before","globals_after","negative_ram","not_reached","repeat","invalid_repeat"};
    printf("{\"flags_bytes\":%zu,\"permanent_data_bytes\":%zu,\"body_cap\":%u,\"frame_capacity\":448,\"cases\":[",
        sizeof(out),sizeof(n10_data),N10_EARLY_BODY_MAX);
    for(i=0;i<14;++i) if(!one(names[i],i,i==0)) return 1;
    n10_early_unavailable(&out,N10_EARLY_NOT_REACHED); memset(&guard,0xa5,sizeof(guard));
    count=n10_early_format(&out,guard.body,sizeof(guard.body),"11111111111111111111111111111111",
        "22222222222222222222222222222222",0);
    short_ok=!count && zeroed(guard.body,sizeof(guard.body));
    for(i=0;i<8;++i) if(guard.left[i]!=0xa5 || guard.right[i]!=0xa5) short_ok=0;
    n10_early_clear(&out); memset(body,0xa5,sizeof(body));
    count=n10_early_format(&out,body,sizeof(body),"11111111111111111111111111111111",
        "22222222222222222222222222222222",0);
    invalid_ok=!count && zeroed(body,sizeof(body));
    printf("],\"short_buffer_rejected\":%u,\"zero_reason_unavailable_rejected\":%u,\"hash_calls\":0,\"decoder_calls\":0}\n",short_ok,invalid_ok);
    return short_ok && invalid_ok ? 0 : 1;
}
