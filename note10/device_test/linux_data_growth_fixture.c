/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual new capture adapter + scalar helper. No decoder/crypto or physical-byte read. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"growth fixture line %u\n",__LINE__); exit(1); } } while(0)
#define N10_DATA_HOST_TEST 1
#define N10_DATA_IMAGE_EXPECTATION 1
#define N10_DATA_COMPARE_EVIDENCE 1
#define N10_DATA_EARLY_CAPTURE_ONLY 1
#define CONFIG_HAVE_MEMBLOCK 1
#define CONFIG_ARM64 1
#define CONFIG_PHYS_ADDR_T_64BIT 1
#define CONFIG_ARM64_VA_BITS 39
#define VA_BITS 39
#define BIT(n) (1ull<<(n))
#define PAGE_OFFSET (UINT64_MAX-BIT(38)+1)
#define READ_ONCE(x) (*(volatile __typeof__(x) *)&(x))
#define RELOC_HIDE(x,o) ((x)+(o))
#define __used __attribute__((used))
#define __init
typedef uint64_t phys_addr_t;
static uint64_t memstart_addr,kimage_voffset,_text,_end;
static unsigned long initrd_start,initrd_end;
static uint64_t expected_begin,expected_length,input_physical;
static unsigned int queries,early_reads,clears48,nonlinear,after_early,after_query;
static int memory_value,map_value,reserved_value;
static void clear(void *p,size_t n)
{
    memset(p,0,n);
    if(n==48) ++clears48;
}
static void copy8(void *p,const void *unused)
{
    (void)unused; ++early_reads; memcpy(p,"N10DATA1",8);
    if(after_early) ++initrd_end;
}
static int memory(uint64_t p,uint64_t n)
{
    if(p==input_physical && n==4096) return 1; /* unchanged early8 guard */
    CHECK(p==expected_begin && n==expected_length); ++queries;
    if(after_query) memstart_addr+=2;
    return memory_value;
}
static int map(uint64_t p)
{
    if(p==input_physical) return 1;
    CHECK(p==expected_begin); ++queries; return map_value;
}
static int reserved(uint64_t p,uint64_t n)
{
    CHECK(p==expected_begin && n==expected_length); ++queries; return reserved_value;
}
#define n10_data_clear(p,n) clear(p,n)
#define N10_EARLY_COPY8(p,s) copy8(p,s)
#define n10_data_linear(x) (!nonlinear && (((uint64_t)(x)&BIT(38))!=0))
#define n10_data_pa(x) (((uint64_t)(x)&~PAGE_OFFSET)+memstart_addr)
#define n10_data_va(x) (((uint64_t)(x)-memstart_addr)|PAGE_OFFSET)
#define n10_data_region_memory(p,n) memory(p,n)
#define n10_data_map_memory(p) map(p)
#define n10_data_region_reserved(p,n) reserved(p,n)
#include "linux_data_carrier.c"
static void reset(void)
{
    memset(&n10_data,0,sizeof(n10_data));
    memstart_addr=0x80000000; _text=PAGE_OFFSET-BIT(38)+0x100000;
    kimage_voffset=_text-0x80000000; _end=_text+0x3500000;
    input_physical=0x80800000;
    initrd_start=(input_physical-memstart_addr)|PAGE_OFFSET; initrd_end=initrd_start+4096;
    expected_begin=_end-kimage_voffset; expected_length=0x3900000-0x3500000;
    queries=early_reads=clears48=nonlinear=after_early=after_query=0;
    memory_value=map_value=1; reserved_value=0;
}
static void direct_guards(void)
{
    unsigned int i;
    for(i=0;i<6;++i) {
        struct n10_data_range range={0};
        struct n10_data_growth out;
        unsigned int captures=1;
        int stable=1;
        reset(); range.checked=1; range.kernel_start=0x80000000; range.kernel_end=0x83500000;
        range.input_start=0x80800000;range.input_end=0x80801000;
        if(i==0) range.checked=0;
        if(i==1) captures=0;
        if(i==2) captures=2;
        if(i==3) stable=0;
        if(i==4) { range.kernel_start=UINT64_MAX-N10_GROWTH_BUDGET+1; range.kernel_end=range.kernel_start+0x3500000; }
        if(i==5) range.kernel_end=range.kernel_start;
        n10_growth_observe(&out,&range,captures,stable);
        CHECK(!out.checked && out.reasons && !queries && clears48==1 && !out.bits);
    }
}
int main(void)
{
    static const char identity[]="11111111111111111111111111111111";
    static const char cycle[]="22222222222222222222222222222222";
    unsigned int i,j;
    char checked[448],unavailable[448],small[128];
    struct n10_data_growth snapshot;
    CHECK(sizeof(n10_data)==120);
    direct_guards();
    reset();n10_growth_snapshot(&snapshot,&n10_data.growth);
    CHECK(snapshot.reasons==N10_GROWTH_UNREACHED && !queries);
    CHECK(n10_growth_format(&snapshot,unavailable,sizeof(unavailable),identity,cycle,0)>0);
    memset(small,0x55,sizeof(small));
    CHECK(n10_growth_format(&snapshot,small,sizeof(small),identity,cycle,0)==0);
    for(j=0;j<sizeof(small);++j) CHECK(small[j]==0);
    for(i=0;i<12;++i) {
        unsigned long start,end;
        reset();
        if(i==1) memory_value=0;
        if(i==2) map_value=0;
        if(i==3) reserved_value=1;
        if(i==4) { input_physical=expected_begin+4096; initrd_start=(input_physical-memstart_addr)|PAGE_OFFSET;initrd_end=initrd_start+4096; }
        if(i==6) nonlinear=1;
        if(i==7) { _end=_text+N10_GROWTH_TARGET;expected_begin=_end-kimage_voffset;expected_length=N10_GROWTH_BUDGET-N10_GROWTH_TARGET; }
        if(i==9) after_early=1;
        if(i==10) after_query=1;
        if(i==11) memory_value=2;
        start=initrd_start;end=initrd_end;
        if(i==5) { start=0;initrd_start=0; }
        if(i==8) ++initrd_end;
        n10_data_capture(start,end);
        if(i<5) {
            CHECK(n10_data.growth.checked==1 && !n10_data.growth.reasons && queries==3 && early_reads==1);
            CHECK(((n10_data.growth.bits>>3)&1)==(i==4));
            CHECK((n10_data.growth.bits&1)==(i==1 ? 0u : 1u));
            CHECK(((n10_data.growth.bits>>1)&1)==(i==2 ? 0u : 1u));
            CHECK(((n10_data.growth.bits>>2)&1)==(i==3 ? 1u : 0u));
            CHECK(clears48>=2);
        } else CHECK(!n10_data.growth.checked && n10_data.growth.reasons && queries==(i>=10 ? 3u : 0u));
        if(i==0) {
            CHECK(n10_growth_format(&n10_data.growth,checked,sizeof(checked),identity,cycle,1)>0);
            n10_data_capture(start,end);
            CHECK(queries==3 && early_reads==1 && n10_data.growth.reasons==N10_GROWTH_REPEAT && !n10_data.growth.bits);
            CHECK(n10_growth_format(&n10_data.growth,small,sizeof(small),identity,cycle,2)==0);
        }
        if(i==10) CHECK(n10_data.growth.reasons==N10_GROWTH_STABLE && n10_data.growth.bits==N10_GROWTH_QUERIED);
        if(i==11) CHECK(n10_data.growth.reasons==N10_GROWTH_QUERY && n10_data.growth.bits==N10_GROWTH_QUERIED);
    }
    printf("{\"capture_cases\":12,\"guard_cases\":6,\"actual_capture_adapter\":true,\"bookkeeping_only\":true,\"permanent_scalar_bytes\":120,\"new_extension_byte_reads\":0,\"new_input_byte_reads\":0,\"old_decoder_calls\":0,\"wire_checked\":\"%s\",\"wire_unavailable\":\"%s\"}\n",checked,unavailable);
    return 0;
}
