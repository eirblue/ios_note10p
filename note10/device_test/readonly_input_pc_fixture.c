/* SPDX-License-Identifier: GPL-2.0-only */
/* Synthetic only: actual new source guard + actual late DATA consumer.
 * Hash/provider and decoder are stubs; unchanged decoder is never executed. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#define READ_ONCE(x) (*(volatile __typeof__(x) *)&(x))
#define RELOC_HIDE(p,o) ({ unsigned long a=(unsigned long)(p); __asm__("" : "+r"(a)); (typeof(p)) (a+(o)); })
#include "readonly_input_pc.h"
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"fixture assertion line %u\n",__LINE__); exit(1); } } while(0)
static struct {
    unsigned char before[16],input[N10_RO_CAPACITY],after[16];
} storage __attribute__((aligned(16)));
#define n10_readonly_input storage.input
static struct n10_ro_descriptor n10_readonly_descriptor;
static unsigned int hashes,decodes,allocations,frees,fail_alloc,fail_hash,mismatch_hash,fail_decode;
static void *blocks[2];
static size_t sizes[2],first_hash;
static unsigned char *snapshot;
static void *fixture_alloc(size_t n)
{
    unsigned char *raw;
    CHECK(allocations<2);
    ++allocations;
    if(allocations==fail_alloc) return NULL;
    raw=malloc(n+32); CHECK(raw); memset(raw,0xa5,n+32);
    blocks[allocations-1]=raw; sizes[allocations-1]=n;
    return raw+16;
}
static void fixture_free(void *p)
{
    unsigned int i;
    size_t j;
    for(i=0;i<2;++i) if(blocks[i] && (unsigned char *)blocks[i]+16==p) {
        unsigned char *raw=blocks[i];
        for(j=0;j<16;++j) CHECK(raw[j]==0xa5 && raw[16+sizes[i]+j]==0xa5);
        for(j=0;j<sizes[i];++j) CHECK(raw[16+j]==0);
        free(raw); blocks[i]=NULL; ++frees; return;
    }
    CHECK(0);
}
#define N10_DATA_HOST_TEST 1
#define N10_DATA_READONLY_PC 1
#define N10_DATA_IMAGE_EXPECTATION 1
#define __used __attribute__((used))
#define __init
#define n10_data_linear(x) ((x)!=0)
#define n10_data_pa(x) ((uint64_t)(x))
#define n10_data_va(x) ((unsigned long)(x))
#define n10_data_clear(p,n) memset(p,0,n)
#define n10_data_alloc(n) fixture_alloc(n)
#define n10_data_free(p) fixture_free(p)
static int n10_data_hash(const void *input,size_t bytes,unsigned char digest[32])
{
    ++hashes;
    if(hashes==1) { CHECK(input==storage.input && bytes==256); first_hash=bytes; }
    else if(hashes==2) CHECK(input==storage.input+128 && bytes==18);
    else CHECK(hashes==3 && bytes==16);
    memset(digest,hashes==mismatch_hash ? 2 : 1,32);
    return hashes==fail_hash ? -5 : 0;
}
int n10_lzma_alone_decode(const uint8_t *input,size_t n,uint8_t *output,size_t cap,
    void *work,size_t wn,struct n10_lzma_result *result)
{
    ++decodes;
    CHECK(input==storage.input+128 && n==18 && cap==16 && wn==N10_LZMA_WORKSPACE);
    memset(output,7,cap); memset(work,0xcc,wn);
    result->version=1; result->status=fail_decode ? -1 : 0;
    result->consumed=n; result->written=cap;
    return result->status;
}
#include "linux_data_carrier.c"
static void le(unsigned char *p,uint64_t n,unsigned int count)
{
    unsigned int i;
    for(i=0;i<count;++i) p[i]=(unsigned char)(n>>(8*i));
}
static void reset(void)
{
    memset(&n10_data,0,sizeof(n10_data));
    memset(&storage,0,sizeof(storage));
    memset(storage.before,0x69,16); memset(storage.after,0x96,16);
    memset(&n10_readonly_descriptor,0,sizeof(n10_readonly_descriptor));
    memcpy(n10_readonly_descriptor.magic,N10_RO_MAGIC,16);
    le(n10_readonly_descriptor.version,1,4); le(n10_readonly_descriptor.bytes,80,4);
    le(n10_readonly_descriptor.capacity,N10_RO_CAPACITY,8);
    hashes=decodes=allocations=frees=fail_alloc=fail_hash=mismatch_hash=fail_decode=0;
    first_hash=0; memset(blocks,0,sizeof(blocks));
}
static void patched(void)
{
    unsigned char *p=storage.input;
    le(n10_readonly_descriptor.logical,256,8); memset(n10_readonly_descriptor.expected,1,32);
    memcpy(p,"N10DATA1",8); le(p+8,1,2); le(p+10,128,2);
    le(p+16,256,8); le(p+24,128,8); le(p+32,18,8); le(p+40,16,8);
    memset(p+48,1,64); p[128]=0x5d; le(p+129,1u<<23,4); le(p+133,16,8);
}
static void intact(void)
{
    unsigned int i;
    CHECK(memcmp(snapshot,storage.input,N10_RO_CAPACITY)==0);
    for(i=0;i<16;++i) CHECK(storage.before[i]==0x69 && storage.after[i]==0x96);
    CHECK(blocks[0]==NULL && blocks[1]==NULL);
}
static void guard_cases(void)
{
    const unsigned char *input;
    unsigned char expected[32];
    uint64_t logical;
    unsigned int variant;
    for(variant=0;variant<10;++variant) {
        size_t cap=N10_RO_CAPACITY,ds=80;
        unsigned int source=N10_RO_SOURCE;
        const unsigned char *slot=(const unsigned char *)(uintptr_t)16;
        int want=variant==0 ? 0 : -1;
        reset();
        if(variant) patched();
        if(variant==1) source=0;
        if(variant==2) --cap;
        if(variant==3) --ds;
        if(variant==4) n10_readonly_descriptor.magic[0]^=1;
        if(variant==5) n10_readonly_descriptor.reserved[7]=1;
        if(variant==6) le(n10_readonly_descriptor.logical,N10_RO_CAPACITY+1,8);
        if(variant==7) slot=(const unsigned char *)(uintptr_t)17;
        if(variant==8) memset(n10_readonly_descriptor.expected,0,32);
        if(variant==9) le(n10_readonly_descriptor.logical,127,8);
        input=(const unsigned char *)(uintptr_t)1; logical=99; memset(expected,0xff,32);
        CHECK(n10_ro_admit(&n10_readonly_descriptor,ds,slot,cap,source,&input,&logical,expected)==want);
        CHECK(input==NULL && logical==0 && hashes==0 && decodes==0);
        for(source=0;source<32;++source) CHECK(expected[source]==0);
    }
}
int main(void)
{
    static const char *names[]={"unpatched","descriptor","ok","carrier_hash","carrier_mismatch",
        "header","stream_hash","output_alloc","work_alloc","decode","payload_hash","repeat"};
    unsigned int i;
    snapshot=malloc(N10_RO_CAPACITY); CHECK(snapshot);
    guard_cases();
    for(i=0;i<sizeof(names)/sizeof(names[0]);++i) {
        struct n10_data_outcome out;
        reset(); if(i) patched();
        if(i==1) n10_readonly_descriptor.version[0]=2;
        if(i==3) fail_hash=1;
        if(i==4) mismatch_hash=1;
        if(i==5) storage.input[0]=0;
        if(i==6) fail_hash=2;
        if(i==7) fail_alloc=1;
        if(i==8) fail_alloc=2;
        if(i==9) fail_decode=1;
        if(i==10) mismatch_hash=3;
        memcpy(snapshot,storage.input,N10_RO_CAPACITY);
        n10_data_run(&out);
        CHECK(out.captures==0 && n10_data.captures==0);
        if(i<2) CHECK(!hashes && !decodes && !out.retained && out.reasons);
        else CHECK(first_hash==256 && out.logical==256 && out.carrier==N10_RO_CAPACITY && out.retained==1);
        if(i==2 || i==11) CHECK(!strcmp(out.status,"ok") && hashes==3 && decodes==1 && frees==2);
        else if(i>=2) CHECK(strcmp(out.status,"ok") && decodes==(i>=9 ? 1u : 0u));
        if(i==11) {
            unsigned int before=hashes;
            n10_data_run(&out);
            CHECK(hashes==before && decodes==1 && out.reasons==N10_DATA_EMIT_REPEAT && !out.retained);
        }
        intact();
    }
    free(snapshot);
    puts("{\"guard_cases\":10,\"consumer_cases\":12,\"actual_new_guard_and_consumer\":true,\"mock_crypto_decoder\":true,\"input_unchanged\":true,\"allocation_canaries_and_clear\":true,\"old_decoder_calls\":0}");
    return 0;
}
