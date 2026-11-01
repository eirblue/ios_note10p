/* SPDX-License-Identifier: GPL-2.0-only */
/* Synthetic API stand-ins exercise NEW snapshot code; no crypto KAT/model. */
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define N10_FDT_HOST_TEST 1
#define __init
#define __aligned(n) __attribute__((aligned(n)))
#define GFP_KERNEL 0
#define N10_SHA256_KAT_ID "11111111111111111111111111111111"
static const char n10_cycle[] = "22222222222222222222222222222222";
static int early = 1, allocations, hashes, copies, crc_calls, fail_mode;
static unsigned long expected_sum;
static size_t allocated_size;
static struct crypto_shash { int placeholder; } provider;
struct shash_desc { struct crypto_shash *tfm; unsigned int flags; };
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
static struct crypto_shash *crypto_alloc_shash(const char *name, int a, int b)
{
    assert(!early && !strcmp(name,"sha256-generic") && !a && !b);
    ++allocations;
    return fail_mode==1 ? (void *)(intptr_t)-ENOENT : &provider;
}
static const char *crypto_shash_driver_name(struct crypto_shash *tfm)
{ assert(tfm==&provider); return fail_mode==2 ? "wrong-provider" : "sha256-generic"; }
static unsigned int crypto_shash_digestsize(struct crypto_shash *tfm)
{ assert(tfm==&provider); return fail_mode==3 ? 64 : 32; }
static unsigned int crypto_shash_descsize(struct crypto_shash *tfm)
{ assert(tfm==&provider); return fail_mode==4 ? 8192 : 104; }
static void *kzalloc(size_t n, int flags)
{ assert(!early && !flags && n<=4096); allocated_size=n; return fail_mode==5 ? NULL : calloc(1,n); }
static void kfree(void *p)
{ size_t i; for(i=0;i<allocated_size;++i) assert(!((unsigned char *)p)[i]); free(p); }
static void crypto_free_shash(struct crypto_shash *tfm) { assert(tfm==&provider); }
static int crypto_shash_digest(struct shash_desc *desc, const unsigned char *data,
                               unsigned int length, unsigned char *out)
{
    unsigned long sum = 0; unsigned int i;
    assert(!early && desc->tfm==&provider && !desc->flags);
    ++hashes;
    memset((char *)desc+sizeof(*desc),0xa5,104);
    for (i=0; i<length; ++i) sum+=data[i];
    assert(sum==expected_sum); /* Original bytes, never the modified caller. */
    if (fail_mode==6) { memset(out,0xa5,32); return -EIO; }
    for (i=0; i<32; ++i) out[i]=(unsigned char)(sum+i);
    return 0;
}
static void memzero_explicit(void *p, size_t n) { memset(p,0,n); }
static void *traced_memcpy(void *to, const void *from, size_t n)
{ if(early) ++copies; return memcpy(to,from,n); }
static int scnprintf(char *out, size_t size, const char *format, ...)
{
    int n; va_list ap; va_start(ap,format); n=vsnprintf(out,size,format,ap); va_end(ap);
    assert(n>=0 && (size_t)n<size); return n;
}
static uint32_t n10_frame_checksum(const char *p, unsigned int n)
{ uint32_t v=2166136261U; while(n--) v=(v^(unsigned char)*p++)*16777619U; return v; }
#define pr_info(format, ...) printf("N10BOOTLINK2 boot=33333333333333333333333333333333 " format, ##__VA_ARGS__)
#define memcpy traced_memcpy
#include "early_fdt_binding.c"
#undef memcpy
static void *initial_boot_params;
static uint32_t of_fdt_crc32;
static unsigned int declared_length;
static int header_invalid;
static int fdt_check_header(void *p) { (void)p; return header_invalid; }
static unsigned int fdt_totalsize(void *p) { (void)p; return declared_length; }
static uint32_t crc32_be(uint32_t seed, void *p, unsigned int length)
{ (void)p; assert(seed==~0U && length==declared_length); ++crc_calls; return 123; }
#include "test-verifier.c"

int main(int argc, char **argv)
{
    unsigned int i, length=64; int verified=-1, cleared=1;
    unsigned char *input;
    assert(argc==2);
    if (!strcmp(argv[1],"minimum")) length=N10_FDT_HEADER;
    if (!strcmp(argv[1],"maximum")) length=N10_FDT_CAPACITY;
    if (!strcmp(argv[1],"short")) length=N10_FDT_HEADER-1;
    if (!strcmp(argv[1],"oversized")) length=N10_FDT_CAPACITY+1;
    input=malloc(length); assert(input); memset(input,7,length);
    expected_sum=7UL*length; declared_length=length;
    if (!strcmp(argv[1],"invalid-header")) header_invalid=1;
    if (strncmp(argv[1],"hash-failure-",13)==0) fail_mode=atoi(argv[1]+13);
    if (strcmp(argv[1],"unavailable"))
        verified=early_init_dt_verify(!strcmp(argv[1],"null") ? NULL : input);
    assert(!allocations && !hashes); /* No early provider/allocator dependency. */
    if (!strcmp(argv[1],"repeat")) {
        memset(input,9,length); early_init_dt_verify(input);
        assert(n10_fdt_snapshot[0]==7); /* First capture never overwritten. */
    }
    memset(input,0xee,length); /* Caller is mutable after the boundary. */
    early=0;
    n10_fdt_binding_init();
    for(i=0;i<N10_FDT_CAPACITY;++i) if(n10_fdt_snapshot[i]) cleared=0;
    printf("{\"copies\":%d,\"allocations\":%d,\"hashes\":%d,\"verified\":%d,\"crc_calls\":%d,\"cleared\":%d}\n",
           copies,allocations,hashes,verified,crc_calls,cleared);
    free(input);return 0;
}
