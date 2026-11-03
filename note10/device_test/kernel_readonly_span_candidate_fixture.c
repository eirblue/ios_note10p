/* SPDX-License-Identifier: GPL-2.0-only */
/* NEW type3 adapter only; crypto/decoder are stubs, no old fixture replay. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"type3 fixture assertion line %u\n",__LINE__);exit(1); } } while(0)
static unsigned char fixture_read(const volatile unsigned char *p);
#define READ_ONCE(x) fixture_read(&(x))
#define RELOC_HIDE(p,o) ({ unsigned long a=(unsigned long)(p); __asm__("" : "+r"(a)); (typeof(p))(a+(o)); })
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
static uintptr_t kernel_start,kernel_end;
#define _stext ((unsigned char *)kernel_start)
#define _end ((unsigned char *)kernel_end)
static unsigned int descriptor_reads,hashes,allocations,decodes,cases;
static unsigned char fixture_read(const volatile unsigned char *p)
{
    uintptr_t a=(uintptr_t)p,start=(uintptr_t)&storage.descriptor;
    CHECK(start<=a && a<start+80);++descriptor_reads;return *p;
}
#define N10_DATA_HOST_TEST 1
#define N10_DATA_KERNEL_READONLY 1
#define N10_DATA_KERNEL_READONLY_V3 1
#define N10_DATA_IMAGE_EXPECTATION 1
#define __used __attribute__((used))
#define __init
#define n10_data_linear(x) ((x)!=0)
#define n10_data_pa(x) ((uint64_t)(x))
#define n10_data_va(x) ((unsigned long)(x))
#define n10_data_clear(p,n) memset(p,0,n)
static void *fixture_alloc(size_t n) { (void)n;++allocations;CHECK(0);return NULL; }
#define n10_data_alloc(n) fixture_alloc(n)
#define n10_data_free(p) free(p)
static int n10_data_hash(const void *p,size_t n,unsigned char digest[32])
{
    CHECK(p==storage.input && n==N10_KRO3_CAPACITY);++hashes;CHECK(hashes==1);
    memset(digest,2,32);return 0;
}
int n10_lzma_alone_decode(const uint8_t *p,size_t n,uint8_t *o,size_t cap,void *w,size_t wn,struct n10_lzma_result *r)
{ (void)p;(void)n;(void)o;(void)cap;(void)w;(void)wn;(void)r;++decodes;CHECK(0);return -1; }
#include "linux_data_carrier.c"
static void le(unsigned char *p,uint64_t value,unsigned int n)
{ unsigned int i;for(i=0;i<n;++i)p[i]=(unsigned char)(value>>(8*i)); }
static void reset(unsigned int patched)
{
    memset(&n10_data,0,sizeof(n10_data));memset(&storage.descriptor,0,80);
    memcpy(storage.descriptor.magic,N10_KRO3_MAGIC,16);
    le(storage.descriptor.version,3,4);le(storage.descriptor.bytes,80,4);le(storage.descriptor.capacity,N10_KRO3_CAPACITY,8);
    if(patched){le(storage.descriptor.logical,N10_KRO3_CAPACITY,8);memset(storage.descriptor.expected,1,32);}
    kernel_start=(uintptr_t)storage.input;kernel_end=(uintptr_t)&storage.descriptor+80;
    descriptor_reads=hashes=allocations=decodes=0;
}
static void type_cases(void)
{
    unsigned int variant,j;
    for(variant=0;variant<11;++variant) {
        const unsigned char *input=(const unsigned char *)(uintptr_t)1;
        const struct n10_kro3_descriptor *descriptor;
        unsigned char expected[32];uint64_t logical=99;
        struct n10_kro_span out;unsigned int source=N10_KRO3_SOURCE;int result;
        reset(variant!=0);descriptor=&storage.descriptor;memset(expected,0xa5,32);
        if(variant==2){memcpy(storage.descriptor.magic,"N10KROINPUTV2!!!",16);le(storage.descriptor.version,2,4);}
        if(variant==3){memcpy(storage.descriptor.magic,"N10ROINPUTPCV1!!",16);le(storage.descriptor.version,1,4);}
        if(variant==4)source=2;
        if(variant==5)le(storage.descriptor.version,2,4);
        if(variant==6)storage.descriptor.reserved[7]=1;
        if(variant==7)kernel_end=(uintptr_t)storage.input+N10_KRO3_CAPACITY-1;
        if(variant==8)descriptor=(const struct n10_kro3_descriptor *)storage.input;
        if(variant==9)kernel_end=kernel_start;
        if(variant==10)le(storage.descriptor.logical,128,8);
        result=n10_kro3_span_admit(&out,kernel_start,kernel_end,descriptor,80,storage.input,N10_KRO3_CAPACITY,source,&input,&logical,expected);
        if(variant<=1)CHECK(result==(int)variant && out.bits==127 && descriptor_reads>0);
        else CHECK(result==-1);
        if(variant==4 || (variant>=7 && variant<=9))CHECK(!descriptor_reads);
        if(variant==1)CHECK(input==storage.input && logical==N10_KRO3_CAPACITY && expected[0]==1);
        else { CHECK(!input && !logical);for(j=0;j<32;++j)CHECK(!expected[j]); }
        CHECK(!hashes && !allocations && !decodes);++cases;
    }
}
int main(void)
{
    struct n10_data_outcome outcome;
    char checked[448],refused[448],unreached[448];
    const char *id="11111111111111111111111111111111",*cycle="22222222222222222222222222222222";
    size_t i;
    memset(storage.before,0x69,16);memset(storage.between,0x96,16);memset(storage.after,0x5a,16);
    CHECK(!strcmp(N10_DATA_EXPECTATION_SOURCE,"kernel-readonly-span-candidate-v1"));
    type_cases();reset(0);n10_data_run(&outcome);
    CHECK(outcome.source_span.bits==127 && !outcome.source_span.reasons && descriptor_reads>0);
    CHECK(outcome.reasons==N10_DATA_EXPECT_UNPATCHED && !hashes && !allocations && !decodes);
    CHECK(n10_kro_span_format(&outcome.source_span,checked,sizeof(checked),id,cycle)>0);
    descriptor_reads=0;n10_data_run(&outcome);CHECK(!descriptor_reads && outcome.reasons==N10_DATA_EMIT_REPEAT);
    CHECK(n10_kro_span_format(&outcome.source_span,unreached,sizeof(unreached),id,cycle)>0);
    reset(1);kernel_end=kernel_start;n10_data_run(&outcome);CHECK(!descriptor_reads && !hashes);
    CHECK(n10_kro_span_format(&outcome.source_span,refused,sizeof(refused),id,cycle)>0);
    /* Actual new guarded late consumer reaches only the synthetic hash stub. */
    reset(1);n10_data_run(&outcome);
    CHECK(outcome.source_span.bits==127 && descriptor_reads>0 && hashes==1 && !allocations && !decodes);
    CHECK(!strcmp(outcome.status,"carrier_mismatch") && !outcome.carrier_rc && !outcome.reasons && outcome.expectations==1 && outcome.retained==1);
    for(i=0;i<16;++i)CHECK(storage.before[i]==0x69 && storage.between[i]==0x96 && storage.after[i]==0x5a);
    printf("{\"type_cases\":%u,\"actual_class3_adapter\":true,\"pre_read_guard\":true,\"synthetic_hash_calls\":1,\"old_decoder_calls\":0,\"allocations\":0,\"input_byte_reads\":0,\"canaries\":true,\"checked\":\"%s\",\"refused\":\"%s\",\"not_reached\":\"%s\"}\n",cases,checked,refused,unreached);
    return 0;
}
