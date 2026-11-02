/* SPDX-License-Identifier: BSD-2-Clause */
/* Controlled globals/conversion/panic; the allocator body is the production include. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#define ARM64_BOARD_CONFIG_EXYNOS9825 1
#define __ARM_16K_PG__ 1
#define CONFIG_SPTM 0
#define XNU_MONITOR 0
#define __ARM_KERNEL_PROTECT__ 0
#define KASAN 0
#define ARM_PGBYTES 16384
#define PAGE_SIZE page_size
#define P UINT64_C(16384)
#define BASE UINT64_C(0x80000000)
typedef uintptr_t vm_offset_t;
static uint64_t page_size, gPhysBase, mem_size, first_avail_phys, avail_start, avail_end;
static unsigned char arena[12 * ARM_PGBYTES];
static unsigned conversions, panics, clears, checks;
static int conversion_failure;
static uint64_t converted_cursor;
static jmp_buf refusal;
static _Noreturn void panic(const char *reason)
{
    if (!reason || !*reason) abort();
    panics++;
    longjmp(refusal, 1);
}
static vm_offset_t phystokv(uint64_t pa)
{
    conversions++;
    converted_cursor = avail_start;
    if (conversion_failure) panic("controlled conversion refusal");
    if (pa < BASE || pa - BASE > sizeof(arena) - ARM_PGBYTES) abort();
    return (vm_offset_t)(arena + (pa - BASE));
}
#include "exynos_checked_ptpage.c"
#define CHECK(c) do { checks++; if (!(c)) { fprintf(stderr,"fixture check %u at %d\n",checks,__LINE__); return 1; } } while (0)
static void reset(void)
{
    page_size=P;gPhysBase=BASE;mem_size=8*P;first_avail_phys=BASE+2*P;
    avail_start=first_avail_phys;avail_end=0;
    conversions=panics=clears=0;conversion_failure=0;converted_cursor=0;
    memset(arena,0xa5,sizeof(arena));
}
static int boot(uint64_t base, uint64_t raw, uint64_t cap)
{
    if (setjmp(refusal)) return 1;
    n10_pt_require_boot_input(base, raw, cap);
    return 0;
}
static int allocate_and_clear(void)
{
    if (setjmp(refusal)) return 1;
    vm_offset_t p=n10_exynos_dynamic_ptpage();
    memset((void *)p,0,ARM_PGBYTES);
    clears++;
    return 0;
}
static int unchanged(size_t begin,size_t end,unsigned char value)
{
    for (size_t i=begin;i<end;i++) if (arena[i]!=value) return 0;
    return 1;
}
static int first_calls(void)
{
    reset();
    CHECK(!boot(BASE,8*P+17,0)); /* native round-down remains valid */
    CHECK(!boot(BASE,8*P,9*P+1)); /* non-capping option is ignored natively */
    CHECK(!allocate_and_clear());
    CHECK(avail_end==0 && avail_start==BASE+3*P && converted_cursor==BASE+2*P);
    avail_end=UINT64_C(0xfeedface);
    CHECK(!allocate_and_clear());
    CHECK(avail_end==UINT64_C(0xfeedface) && avail_start==BASE+4*P && converted_cursor==BASE+3*P);
    CHECK(conversions==2 && clears==2 && panics==0);
    CHECK(unchanged(0,2*P,0xa5));
    CHECK(unchanged(2*P,4*P,0));
    CHECK(unchanged(4*P,sizeof(arena),0xa5));
    return 0;
}
static int refusals(void)
{
    static const uint64_t raw[][3]={
        {BASE,0,0},{BASE,1,0},{BASE+1,8*P,0},
        {UINT64_MAX-P+1,2*P,0},{BASE,8*P,1},{BASE,8*P,3*P+1}
    };
    for(size_t i=0;i<sizeof(raw)/sizeof(raw[0]);i++) {
        reset();uint64_t cursor=avail_start;
        CHECK(boot(raw[i][0],raw[i][1],raw[i][2]));
        CHECK(panics==1 && !conversions && !clears && avail_start==cursor);
        CHECK(unchanged(0,sizeof(arena),0xa5));
    }
    /* base, managed, floor, cursor, page: every refusal also reaches real wrapper. */
    static const uint64_t bad[][5]={
        {BASE,0,BASE,BASE,P},{BASE+1,8*P,BASE+2*P,BASE+2*P,P},
        {BASE,8*P-1,BASE+2*P,BASE+2*P,P},
        {UINT64_MAX-P+1,2*P,UINT64_MAX-P+1,UINT64_MAX-P+1,P},
        {BASE,8*P,BASE-P,BASE+P,P},{BASE,8*P,BASE+3*P,BASE+2*P,P},
        {BASE,8*P,BASE+2*P,BASE+9*P,P},{BASE,8*P,BASE+2*P,BASE+8*P,P},
        {BASE,8*P,BASE+2*P+1,BASE+3*P,P},{BASE,8*P,BASE+2*P,BASE+3*P+1,P},
        {BASE,8*P,BASE+2*P,BASE+3*P,4096}
    };
    for(size_t i=0;i<sizeof(bad)/sizeof(bad[0]);i++) {
        reset();uint64_t next=UINT64_C(0x12345678);
        CHECK(!n10_pt_next(bad[i][0],bad[i][1],bad[i][2],bad[i][3],bad[i][4],&next));
        CHECK(next==UINT64_C(0x12345678));
        gPhysBase=bad[i][0];mem_size=bad[i][1];first_avail_phys=bad[i][2];avail_start=bad[i][3];page_size=bad[i][4];
        CHECK(allocate_and_clear());
        CHECK(avail_start==bad[i][3] && panics==1 && !conversions && !clears);
        CHECK(unchanged(0,sizeof(arena),0xa5));
    }
    reset();conversion_failure=1;
    CHECK(allocate_and_clear());
    CHECK(conversions==1 && panics==1 && !clears && avail_start==BASE+2*P);
    CHECK(unchanged(0,sizeof(arena),0xa5));
    return 0;
}
static int capped_loop(void)
{
    reset();
    CHECK(!boot(BASE,9*P+123,6*P));
    mem_size=6*P;avail_end=UINT64_MAX;
    for(uint64_t cursor=BASE+2*P;cursor<BASE+6*P;cursor+=P) {
        CHECK(avail_start==cursor);
        CHECK(!allocate_and_clear());
        CHECK(converted_cursor==cursor && avail_start==cursor+P);
    }
    CHECK(avail_start==BASE+6*P && conversions==4 && clears==4);
    CHECK(allocate_and_clear());
    CHECK(avail_start==BASE+6*P && conversions==4 && clears==4 && panics==1);
    CHECK(unchanged(0,2*P,0xa5));
    CHECK(unchanged(2*P,6*P,0));
    CHECK(unchanged(6*P,sizeof(arena),0xa5));
    return 0;
}
int main(int argc,char **argv)
{
    if(argc!=2) return 2;
    int result;
    if(!strcmp(argv[1],"first")) result=first_calls();
    else if(!strcmp(argv[1],"refusals")) result=refusals();
    else if(!strcmp(argv[1],"loop")) result=capped_loop();
    else return 2;
    if(result) return result;
    printf("{\"success\":true,\"mode\":\"%s\",\"checks\":%u,\"conversion_calls\":%u,\"caller_page_clears\":%u,\"panics\":%u}\n",argv[1],checks,conversions,clears,panics);
    return 0;
}
