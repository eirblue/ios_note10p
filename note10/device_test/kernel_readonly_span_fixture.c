/* SPDX-License-Identifier: GPL-2.0-only */
/* NEW composite arithmetic guard and actual late adapter; synthetic only. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"span fixture assertion line %u\n",__LINE__);exit(1); } } while(0)
static unsigned char fixture_read(const volatile unsigned char *p);
#define READ_ONCE(x) fixture_read(&(x))
#define RELOC_HIDE(p,o) ({ unsigned long a=(unsigned long)(p); __asm__("" : "+r"(a)); (typeof(p))(a+(o)); })
#include "kernel_readonly_input.h"
static struct {
    unsigned char before[16],input[N10_KRO_CAPACITY],between[16];
    struct n10_kro_descriptor descriptor;
    unsigned char after[16];
} storage __attribute__((aligned(16)));
#define n10_kernel_readonly_input storage.input
#define n10_kernel_readonly_descriptor storage.descriptor
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
#define N10_DATA_KERNEL_SPAN_PC 1
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
{ (void)p;(void)n;(void)digest;++hashes;CHECK(0);return -1; }
int n10_lzma_alone_decode(const uint8_t *p,size_t n,uint8_t *o,size_t cap,void *w,size_t wn,struct n10_lzma_result *r)
{ (void)p;(void)n;(void)o;(void)cap;(void)w;(void)wn;(void)r;++decodes;CHECK(0);return -1; }
#include "linux_data_carrier.c"
static void le(unsigned char *p,uint64_t value,unsigned int n)
{ unsigned int i;for(i=0;i<n;++i)p[i]=(unsigned char)(value>>(8*i)); }
static void reset(void)
{
    memset(&n10_data,0,sizeof(n10_data));memset(&storage.descriptor,0,80);
    memcpy(storage.descriptor.magic,N10_KRO_MAGIC,16);
    le(storage.descriptor.version,2,4);le(storage.descriptor.bytes,80,4);le(storage.descriptor.capacity,N10_KRO_CAPACITY,8);
    kernel_start=(uintptr_t)storage.input;kernel_end=(uintptr_t)&storage.descriptor+80;
    descriptor_reads=hashes=allocations=decodes=0;
}
static void direct_cases(void)
{
    unsigned int variant,j;
    for(variant=0;variant<15;++variant) {
        const unsigned char *slot,*input=(const unsigned char *)(uintptr_t)1;
        const struct n10_kro_descriptor *descriptor;
        unsigned char expected[32];uint64_t logical=99;
        uintptr_t start,end;size_t cap=N10_KRO_CAPACITY,ds=80;
        struct n10_kro_span out;
        int result;
        reset();slot=storage.input;descriptor=&storage.descriptor;start=kernel_start;end=kernel_end;
        memset(expected,0xa5,32);
        if(variant==1)end=(uintptr_t)slot+N10_KRO_CAPACITY-1;
        if(variant==2)end=(uintptr_t)descriptor+79;
        if(variant==3)end=start;
        if(variant==4)end=start-1;
        if(variant==5)start=0;
        if(variant==6)slot=NULL;
        if(variant==7)descriptor=NULL;
        if(variant==8)slot=(const unsigned char *)(UINTPTR_MAX-N10_KRO_CAPACITY+1);
        if(variant==9)descriptor=(const struct n10_kro_descriptor *)(UINTPTR_MAX-78);
        if(variant==10)descriptor=(const struct n10_kro_descriptor *)slot;
        if(variant==11)--cap;
        if(variant==12)--ds;
        if(variant==13)end=start+N10_KRO_SPAN_BUDGET+1;
        if(variant==14) {
            le(storage.descriptor.logical,N10_KRO_CAPACITY,8);memset(storage.descriptor.expected,1,32);
        }
        result=n10_kro_span_admit(&out,start,end,descriptor,ds,slot,cap,N10_KRO_SOURCE,&input,&logical,expected);
        if(variant==0 || variant==14) {
            CHECK(result==(variant==14 ? 1 : 0) && out.bits==127 && !out.reasons && descriptor_reads>0);
            if(variant==14)CHECK(input==slot && logical==N10_KRO_CAPACITY && expected[0]==1);
        } else CHECK(result==-1 && descriptor_reads==0 && out.reasons && !(out.bits&32));
        if(variant!=14) {
            CHECK(!input && !logical);for(j=0;j<32;++j)CHECK(expected[j]==0);
        }
        CHECK(!hashes && !allocations && !decodes);++cases;
    }
}
int main(void)
{
    struct n10_data_outcome outcome;
    struct n10_kro_span state;
    char checked[448],refused[448],unreached[448],small[16],bad[448];
    const char *id="11111111111111111111111111111111",*cycle="22222222222222222222222222222222";
    size_t i;
    memset(storage.before,0x69,16);memset(storage.between,0x96,16);memset(storage.after,0x5a,16);
    direct_cases();reset();
    /* Actual production adapter: full containment precedes generic/unpatched refusal. */
    n10_data_run(&outcome);
    CHECK(outcome.source_span.bits==127 && !outcome.source_span.reasons && descriptor_reads>0);
    CHECK(outcome.reasons==N10_DATA_EXPECT_UNPATCHED && !strcmp(outcome.status,"unavailable"));
    CHECK(!hashes && !allocations && !decodes);
    CHECK(n10_kro_span_format(&outcome.source_span,checked,sizeof(checked),id,cycle)>0);
    /* Repeat early return retains an explicit NOT_REACHED wire, without any new read. */
    descriptor_reads=0;n10_data_run(&outcome);
    CHECK(!descriptor_reads && outcome.reasons==N10_DATA_EMIT_REPEAT);
    CHECK(n10_kro_span_format(&outcome.source_span,unreached,sizeof(unreached),id,cycle)>0);
    reset();kernel_end=kernel_start;n10_data_run(&outcome);
    CHECK(!descriptor_reads && outcome.source_span.reasons==N10_KRO_SPAN_KERNEL);
    CHECK(n10_kro_span_format(&outcome.source_span,refused,sizeof(refused),id,cycle)>0);
    memset(small,0xa5,sizeof(small));CHECK(!n10_kro_span_format(&outcome.source_span,small,sizeof(small),id,cycle));
    for(i=0;i<sizeof(small);++i)CHECK(!small[i]);
    n10_kro_span_unreached(&state);state.reasons=0;memset(bad,0xa5,sizeof(bad));
    CHECK(!n10_kro_span_format(&state,bad,sizeof(bad),id,cycle));for(i=0;i<sizeof(bad);++i)CHECK(!bad[i]);
    for(i=0;i<16;++i)CHECK(storage.before[i]==0x69 && storage.between[i]==0x96 && storage.after[i]==0x5a);
    printf("{\"guard_cases\":%u,\"actual_adapter\":true,\"descriptor_reads_blocked\":true,\"input_byte_reads\":0,\"hashes\":0,\"allocations\":0,\"old_decoder_calls\":0,\"canaries\":true,\"checked\":\"%s\",\"refused\":\"%s\",\"not_reached\":\"%s\"}\n",cases,checked,refused,unreached);
    return 0;
}
