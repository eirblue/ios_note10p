/* SPDX-License-Identifier: GPL-2.0-only */
/* Only NEW stage boundaries in production n10_data_run; no real decoder/crypto. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "carrier_lzma.h"
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"stage assertion %u case %u\n",__LINE__,variant);exit(1); } } while(0)
static unsigned int variant;
#define READ_ONCE(x) (x)
#define RELOC_HIDE(p,o) ((p)+(o))
#define N10_KRO_SPAN_CLEAR(p,n) memset(p,0,n)
#include "kernel_readonly_span_candidate.h"
#undef N10_KRO_SPAN_CLEAR
static struct {
    unsigned char before[16],input[N10_KRO3_CAPACITY],between[16];
    struct n10_kro3_descriptor descriptor;
    unsigned char after[16];
} storage __attribute__((aligned(16)));
#define n10_kernel_readonly3_input storage.input
#define n10_kernel_readonly3_descriptor storage.descriptor
#define _stext storage.input
#define _end ((unsigned char *)&storage.descriptor+80)
#define N10_DATA_HOST_TEST 1
#define N10_DATA_KERNEL_READONLY 1
#define N10_DATA_KERNEL_READONLY_V3 1
#define N10_DATA_STAGE_WITNESS 1
#define N10_DATA_IMAGE_EXPECTATION 1
#define __used __attribute__((used))
#define __init
#define n10_data_linear(x) ((x)!=0)
#define n10_data_pa(x) ((uint64_t)(x))
#define n10_data_va(x) ((unsigned long)(x))
static struct { unsigned char before[16],body[32],after[16]; } output_region;
static struct { unsigned char before[16],body[N10_LZMA_WORKSPACE],after[16]; } work_region;
static unsigned int allocs,hashes,decodes,clears,frees,live_output,live_work;
static char events[64];static unsigned int event_count;
static void event(char c) { CHECK(event_count+1<sizeof(events));events[event_count++]=c;events[event_count]=0; }
static void *fixture_alloc(size_t n)
{
    ++allocs;
    if(allocs==1) { CHECK(n==32);event('O');if(variant==2)return NULL;live_output=1;return output_region.body; }
    CHECK(allocs==2 && n==N10_LZMA_WORKSPACE);event('W');if(variant==3)return NULL;live_work=1;return work_region.body;
}
static void fixture_clear(void *p,size_t n)
{
    if(p==output_region.body) { CHECK(live_output && n==32);++clears;event('o'); }
    if(p==work_region.body) { CHECK(live_work && n==N10_LZMA_WORKSPACE);++clears;event('w'); }
    memset(p,0,n);
}
static void fixture_free(void *p)
{
    size_t i;
    if(p==work_region.body) { CHECK(live_work);live_work=0;event('x');for(i=0;i<N10_LZMA_WORKSPACE;++i)CHECK(!work_region.body[i]); }
    else { CHECK(p==output_region.body && live_output);live_output=0;event('y');for(i=0;i<32;++i)CHECK(!output_region.body[i]); }
    ++frees;
}
#define n10_data_alloc(n) fixture_alloc(n)
#define n10_data_clear(p,n) fixture_clear(p,n)
#define n10_data_free(p) fixture_free(p)
static int n10_data_hash(const void *p,size_t n,unsigned char digest[32])
{
    ++hashes;
    if(hashes==1) { CHECK(p==storage.input && n==N10_KRO3_CAPACITY);event('C');memset(digest,1,32);return 0; }
    if(hashes==2) { CHECK(p==storage.input+128 && n==18);event('S');memset(digest,variant==9 ? 4 : 2,32);return 0; }
    CHECK(hashes==3 && p==output_region.body && n==32 && live_output);event('H');
    memset(digest,variant==10 ? 4 : 3,32);return variant==11 ? -1 : 0;
}
int n10_lzma_alone_decode(const uint8_t *p,size_t n,uint8_t *out,size_t cap,void *work,size_t wn,struct n10_lzma_result *r)
{
    ++decodes;CHECK(decodes==1 && p==storage.input+128 && n==18 && out==output_region.body && cap==32 &&
        work==work_region.body && wn==N10_LZMA_WORKSPACE && live_output && live_work);event('D');
    memset(out,0xa5,32);memset(work,0x5a,wn);
    r->version=variant==5 ? 2 : 1;r->status=variant==6 ? -1 : 0;
    r->written=variant==7 ? 31 : 32;r->consumed=variant==8 ? 19 : 18;
    return variant==4 ? -1 : 0;
}
#include "linux_data_carrier.c"
static void le(unsigned char *p,uint64_t value,unsigned int n)
{ unsigned int i;for(i=0;i<n;++i)p[i]=(unsigned char)(value>>(8*i)); }
static void reset(void)
{
    memset(&n10_data,0,sizeof(n10_data));memset(&storage,0,sizeof(storage));
    memset(&output_region,0x69,sizeof(output_region));memset(&work_region,0x69,sizeof(work_region));
    memset(storage.before,0x69,16);memset(storage.between,0x69,16);memset(storage.after,0x69,16);
    memcpy(storage.descriptor.magic,N10_KRO3_MAGIC,16);le(storage.descriptor.version,3,4);le(storage.descriptor.bytes,80,4);
    le(storage.descriptor.capacity,N10_KRO3_CAPACITY,8);le(storage.descriptor.logical,N10_KRO3_CAPACITY,8);memset(storage.descriptor.expected,1,32);
    memcpy(storage.input,variant==1 ? "BADMAGIC" : "N10DATA1",8);le(storage.input+8,1,2);le(storage.input+10,128,2);
    le(storage.input+16,N10_KRO3_CAPACITY,8);le(storage.input+24,128,8);le(storage.input+32,18,8);le(storage.input+40,32,8);
    memset(storage.input+48,2,32);memset(storage.input+80,3,32);
    storage.input[128]=0x5d;le(storage.input+129,1u<<23,4);le(storage.input+133,32,8);
    allocs=hashes=decodes=clears=frees=live_output=live_work=event_count=0;events[0]=0;
}
static uint32_t cleanup_work(void) { return N10_SW_WORK_CLEAR_CALLED|N10_SW_WORK_CLEAR_RETURNED|N10_SW_WORK_FREE_CALLED|N10_SW_WORK_FREE_RETURNED; }
static uint32_t cleanup_output(void) { return N10_SW_OUTPUT_CLEAR_CALLED|N10_SW_OUTPUT_CLEAR_RETURNED|N10_SW_OUTPUT_FREE_CALLED|N10_SW_OUTPUT_FREE_RETURNED; }
int main(void)
{
    struct n10_data_outcome out;unsigned int i;uint32_t wanted;
    char body[448];
    CHECK(sizeof(out)==128 && sizeof(n10_data)==88);
    for(variant=0;variant<12;++variant) {
        reset();n10_data_run(&out);
        CHECK(!live_output && !live_work && clears==frees && out.retained==1);
        wanted=N10_SW_HEADER_ENTER;
        if(variant!=1)wanted|=N10_SW_HEADER_OK;
        if(variant!=1 && variant!=9)wanted|=N10_SW_STREAM_OK;
        if(variant!=1 && variant!=3 && variant!=9)wanted|=cleanup_work();
        if(variant!=1 && variant!=2 && variant!=9)wanted|=cleanup_output();
        if(variant!=1 && variant!=2 && variant!=3 && variant!=9) {
            wanted|=N10_SW_DECODE_CALLED|N10_SW_DECODE_RETURNED;
            if(variant!=4 && variant!=5 && variant!=6) {
                wanted|=N10_SW_API_OK|N10_SW_LENGTH_ENTER;
                if(variant!=7 && variant!=8) {
                    wanted|=N10_SW_LENGTH_OK|N10_SW_HASH_CALLED|N10_SW_HASH_RETURNED;
                    if(variant!=11)wanted|=N10_SW_DIGEST_ENTER;
                    if(variant!=10 && variant!=11)wanted|=N10_SW_DIGEST_OK;
                }
            }
        }
        CHECK(out.decoded==wanted);
        if(variant==1)CHECK(!strcmp(events,"C") && hashes==1 && !allocs && !decodes && !frees);
        else if(variant==9)CHECK(!strcmp(events,"CS") && hashes==2 && !allocs && !decodes && !frees);
        else if(variant==2)CHECK(!strcmp(events,"CSOWwx") && allocs==2 && frees==1 && !decodes);
        else if(variant==3)CHECK(!strcmp(events,"CSOWoy") && allocs==2 && frees==1 && !decodes);
        else if(variant>=4 && variant<=8)CHECK(!strcmp(events,"CSOWDwxoy") && decodes==1 && hashes==2 && allocs==2 && frees==2);
        else CHECK(!strcmp(events,"CSOWDHwxoy") && decodes==1 && hashes==3 && allocs==2 && frees==2);
        CHECK((!strcmp(out.status,"ok"))==(variant==0));
        CHECK(N10_STAGE_CALLS(&out)==decodes);
        for(i=0;i<16;++i)CHECK(storage.before[i]==0x69 && storage.between[i]==0x69 && storage.after[i]==0x69 &&
            output_region.before[i]==0x69 && output_region.after[i]==0x69 && work_region.before[i]==0x69 && work_region.after[i]==0x69);
        CHECK(n10_stage_format(out.decoded,body,sizeof(body),"11111111111111111111111111111111","22222222222222222222222222222222")>0);
    }
    printf("{\"cases\":12,\"actual_n10_data_run\":true,\"synthetic_only\":true,\"outcome_bytes\":%zu,\"state_bytes\":%zu,\"call_order_counts\":true,\"canaries\":true,\"no_double_free\":true,\"real_decoder_calls\":0}\n",sizeof(out),sizeof(n10_data));
    return 0;
}
