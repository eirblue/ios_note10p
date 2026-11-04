/* SPDX-License-Identifier: GPL-2.0-only */
/* NEW production prefree observation only. Allocator/hash/decoder adapters are synthetic; no native operation. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <stdarg.h>
#include "carrier_lzma.h"
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"new native scope check %u case %u\n",__LINE__,variant);exit(1); } } while(0)
static unsigned int variant;
#define READ_ONCE(x) (x)
#define RELOC_HIDE(p,o) ((p)+(o))
#define N10_KRO_SPAN_CLEAR(p,n) memset(p,0,n)
#include "kernel_readonly_span_candidate.h"
#undef N10_KRO_SPAN_CLEAR
static struct { unsigned char before[16],input[N10_KRO3_CAPACITY],between[16];struct n10_kro3_descriptor descriptor;unsigned char after[16]; } storage __attribute__((aligned(16)));
#define n10_kernel_readonly3_input storage.input
#define n10_kernel_readonly3_descriptor storage.descriptor
#define _stext storage.input
#define _end ((unsigned char *)&storage.descriptor+80)
#define N10_DATA_HOST_TEST 1
#define N10_DATA_KERNEL_READONLY 1
#define N10_DATA_KERNEL_READONLY_V3 1
#define N10_DATA_STAGE_WITNESS 1
#define N10_DATA_SCOPED_OUTPUT 1
#define N10_DATA_PREFREE_OUTPUT_ZERO 1
#define N10_SCOPED_OUTPUT_EMIT_FIXTURE 1
#define N10_DATA_IMAGE_EXPECTATION 1
#define N10_SHA256_KAT_ID "11111111111111111111111111111111"
static const char n10_cycle[]="22222222222222222222222222222222";
#define __used __attribute__((used))
#define __init
#define n10_data_linear(x) ((x)!=0)
#define n10_data_pa(x) ((uint64_t)(x))
#define n10_data_va(x) ((unsigned long)(x))
static struct { unsigned char before[16],body[32],after[16]; } output_region;
static struct { unsigned char before[16],body[N10_LZMA_WORKSPACE],after[16]; } work_region;
static unsigned int allocs,successes,hashes,decodes,output_frees,work_frees,reads,live_output,live_work,frames,lease_flags,stage_flags;
static unsigned int scan_reads,free_reads,free_nonzero,clear_returned,zero_frames;
static unsigned int wire_capacity,wire_reads,wire_nonzero;
static char events[96];static unsigned int event_count;
static void event(char c) { CHECK(event_count+1<sizeof(events));events[event_count++]=c;events[event_count]=0; }
static void *fixture_alloc(size_t n)
{
    ++allocs;
    if(allocs==1) { CHECK(n==32);event('O');if(variant==3)return NULL;live_output=1;++successes;return output_region.body; }
    CHECK(allocs==2 && n==N10_LZMA_WORKSPACE);event('W');live_work=1;++successes;return work_region.body;
}
static void fixture_clear(void *p,size_t n)
{
    if(p==output_region.body) { CHECK(live_output && n==32);event('o'); }
    if(p==work_region.body) { CHECK(live_work && n==N10_LZMA_WORKSPACE);event('w'); }
    memset(p,0,n);
    if(p==output_region.body) { if(variant==2) { output_region.body[7]=1;output_region.body[31]=2; } clear_returned=1; }
}
static void fixture_free(void *p)
{
    if(p==work_region.body) { CHECK(live_work);live_work=0;++work_frees;event('x'); }
    else {
        unsigned int i;const volatile unsigned char *q=p;
        CHECK(p==output_region.body && live_output && clear_returned && scan_reads==32);
        for(i=0;i<32;++i) { unsigned char value=q[i];++free_reads;if(value)++free_nonzero; }
        CHECK(free_nonzero==(variant==2?2u:0u));live_output=0;++output_frees;event('y');
    }
}
static unsigned char fixture_output_read(const unsigned char *p)
{
    CHECK(live_output && !live_work && reads<2);
    CHECK(p==(reads ? output_region.body+31 : output_region.body));
    ++reads;event(reads==1?'f':'l');return *(const volatile unsigned char *)p;
}
static unsigned char fixture_scan(const unsigned char *p)
{
    CHECK(live_output && !live_work && clear_returned && scan_reads<32 && p==output_region.body+scan_reads);
    ++scan_reads;event('z');return *(const volatile unsigned char *)p;
}
#define N10_PREFREE_READ_ONCE(x) fixture_scan(&(x))
#define N10_OUTPUT_READ_ONCE(x) fixture_output_read(&(x))
#define n10_data_alloc(n) fixture_alloc(n)
#define n10_data_clear(p,n) fixture_clear(p,n)
#define n10_data_free(p) fixture_free(p)
static int n10_data_hash(const void *p,size_t n,unsigned char digest[32])
{
    ++hashes;
    if(hashes==1) { CHECK(p==storage.input && n==N10_KRO3_CAPACITY);event('C');memset(digest,1,32);return 0; }
    if(hashes==2) { CHECK(p==storage.input+128 && n==18);event('S');memset(digest,2,32);return 0; }
    CHECK(hashes==3 && p==output_region.body && n==32 && live_output);event('H');memset(digest,3,32);return 0;
}
int n10_lzma_alone_decode(const uint8_t *p,size_t n,uint8_t *out,size_t cap,void *work,size_t wn,struct n10_lzma_result *r)
{
    ++decodes;CHECK(decodes==1 && p==storage.input+128 && n==18 && out==output_region.body && cap==32 &&
        work==work_region.body && wn==N10_LZMA_WORKSPACE && live_output && live_work);event('D');
    memset(out,0xa5,32);memset(work,0x5a,wn);r->version=1;r->status=variant==1?1:0;r->written=variant==1?7:32;r->consumed=18;return variant==1?-1:0;
}
static int scnprintf(char *p,size_t cap,const char *fmt,...)
{
    int count;va_list args;va_start(args,fmt);count=vsnprintf(p,cap,fmt,args);va_end(args);
    return count<0?count:((size_t)count>=cap?(int)cap-1:count);
}
static unsigned int n10_frame_checksum(const char *p,unsigned int n)
{ unsigned int i,value=2166136261u;for(i=0;i<n;++i)value=(value^(unsigned char)p[i])*16777619u;return value; }
static void fixture_emit(const char *format,const char *body,unsigned int checksum)
{
    const char *p;(void)checksum;
    CHECK(!live_output && !live_work && strlen(body)<448);++frames;
    if(strstr(format,"N10OUTPUTZERO1")) {
        ++zero_frames;
        p=strstr(body,"capacity=");CHECK(p);wire_capacity=(unsigned int)strtoul(p+9,NULL,10);
        p=strstr(body,"reads=");CHECK(p);wire_reads=(unsigned int)strtoul(p+6,NULL,10);
        p=strstr(body,"nonzero=");CHECK(p);wire_nonzero=(unsigned int)strtoul(p+8,NULL,10);
        CHECK(wire_capacity==(variant==3?0u:32u) && wire_reads==wire_capacity && wire_nonzero==(variant==2?2u:0u));
        CHECK(strstr(body,variant==3?"scan_called=0 scan_returned=0 observed_zero=0":"scan_called=1 scan_returned=1"));
        CHECK(strstr(body,(variant==2 || variant==3)?"observed_zero=0":"observed_zero=1"));
        CHECK(strstr(body,variant==3?"free_result=not_called":"free_result=void_returned"));
    }
    if(variant==2 && strstr(format,"N10DATARO3"))CHECK(strstr(body,"status=output_zero_observation"));
    if(strstr(format,"N10OUTPUTLEASE1")) { p=strstr(body,"flags=");CHECK(p);lease_flags=(unsigned int)strtoul(p+6,NULL,16); }
    if(strstr(format,"N10DATASTAGE1")) { p=strstr(body,"bits=");CHECK(p);stage_flags=(unsigned int)strtoul(p+5,NULL,16); }
}
#define pr_info(f,b,c) fixture_emit(f,b,c)
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
    memcpy(storage.input,"N10DATA1",8);le(storage.input+8,1,2);le(storage.input+10,128,2);le(storage.input+16,N10_KRO3_CAPACITY,8);
    le(storage.input+24,128,8);le(storage.input+32,18,8);le(storage.input+40,32,8);
    memset(storage.input+48,2,32);memset(storage.input+80,3,32);storage.input[128]=0x5d;le(storage.input+129,1u<<23,4);le(storage.input+133,32,8);
    allocs=successes=hashes=decodes=output_frees=work_frees=reads=live_output=live_work=frames=lease_flags=stage_flags=event_count=0;events[0]=0;
    scan_reads=free_reads=free_nonzero=clear_returned=zero_frames=wire_capacity=wire_reads=wire_nonzero=0;
}
int main(void)
{
    struct n10_data_outcome out;struct n10_output_handle h;unsigned int i;
    unsigned int total_allocs=0,total_successes=0,total_frees=0,total_scans=0,total_free_reads=0,total_nonzero=0,total_frames=0;
    CHECK(sizeof(out)==128 && sizeof(n10_data)==88 && sizeof(h)==24);
    for(variant=0;variant<5;++variant) {
        reset();
        if(variant<4) {
            CHECK(!n10_data_emit());CHECK(frames==5 && zero_frames==1);
            if(variant==1)CHECK(wire_capacity==32 && wire_reads==32); /* partial decode written7 != allocation32 */
        } else {
            memset(&h,0,sizeof(h));n10_data_run(&out,&h);CHECK(live_output && !live_work);
            h.flags|=N10_OUT_BORROWED; /* affected cleanup after consumer refusal */
            n10_scoped_output_finish(&out,&h);
            CHECK(!strcmp(out.status,"output_consumer") && !h.data && h.bytes==32 && h.scanned==32 && !h.nonzero);
            CHECK(h.flags&N10_OUT_FREE_RETURNED);n10_scoped_output_finish(&out,&h);
            CHECK(output_frees==1 && scan_reads==32);
        }
        CHECK(!live_output && !live_work && output_frees+work_frees==successes);
        CHECK(scan_reads==(variant==3?0u:32u) && free_reads==scan_reads && free_nonzero==(variant==2?2u:0u));
        for(i=0;i<16;++i)CHECK(output_region.before[i]==0x69 && output_region.after[i]==0x69 && work_region.before[i]==0x69 && work_region.after[i]==0x69);
        total_allocs+=allocs;total_successes+=successes;total_frees+=output_frees+work_frees;
        total_scans+=scan_reads;total_free_reads+=free_reads;total_nonzero+=free_nonzero;total_frames+=frames;
    }
    CHECK(total_allocs==10 && total_successes==9 && total_frees==9 && total_scans==128 && total_free_reads==128 && total_nonzero==2 && total_frames==20);
    printf("{\"schema\":\"n10-native-prefree-output-zero-fixture-v1\",\"cases\":5,\"allocation_attempts\":%u,\"allocation_successes\":%u,\"free_calls\":%u,\"scan_reads\":%u,\"independent_free_boundary_reads\":%u,\"nonzero_bytes_negative_case\":%u,\"emit_frames\":%u,\"partial_decode_written\":7,\"partial_allocated_capacity\":32,\"handle_bytes\":24,\"outcome_bytes\":128,\"state_bytes\":88,\"scratch_bytes\":448,\"actual_n10_data_run_and_emit\":true,\"synthetic_only\":true,\"exact_cleanup\":true,\"after_free_reads\":0,\"secure_erasure_attested\":false,\"real_decoder_calls\":0,\"native_allocator_executed\":false,\"hardware_operations\":0}\n",
        total_allocs,total_successes,total_frees,total_scans,total_free_reads,total_nonzero,total_frames);
    return 0;
}
