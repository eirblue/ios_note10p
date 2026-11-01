/* Canonical new C control flow only. Stubs do not prove Linux crypto behavior. */
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define N10_SHA256_KAT_HOST_TEST 1
#define __init
#define late_initcall(fn)
#define GFP_KERNEL 0
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define pr_info printf
struct crypto_shash { int unused; };
struct shash_desc { struct crypto_shash *tfm; unsigned int flags; unsigned char ctx[]; };
static struct crypto_shash transform;
static int scenario, tfm_live, desc_live, digests, allocs, frees, desc_allocs;
static unsigned int descriptor_bytes;
static struct crypto_shash *crypto_alloc_shash(const char *name, unsigned int type, unsigned int mask)
{
 assert(!strcmp(name, "sha256-generic") && !type && !mask);
 allocs++;
 if (scenario == 1) return (struct crypto_shash *)(intptr_t)-ENOENT;
 tfm_live++;
 return &transform;
}
static const char *crypto_shash_driver_name(struct crypto_shash *tfm)
{ assert(tfm == &transform && tfm_live == 1); return scenario == 2 ? "other-driver" : "sha256-generic"; }
static unsigned int crypto_shash_digestsize(struct crypto_shash *tfm)
{ assert(tfm == &transform); return scenario == 3 ? 64 : 32; }
static unsigned int crypto_shash_descsize(struct crypto_shash *tfm)
{
 assert(tfm == &transform);
 if (scenario == 4) return 4097;
 if (scenario == 8) return 4096 - sizeof(struct shash_desc);
 if (scenario == 9) return UINT_MAX;
 return 96;
}
static void *kzalloc(size_t size, int flags)
{
 void *p;
 assert(!flags && size <= 4096);
 desc_allocs++;
 descriptor_bytes = (unsigned int)size;
 if (scenario == 5) return NULL;
 p = calloc(1, size);
 assert(p);
 desc_live++;
 return p;
}
static void kfree(void *p)
{ assert(p && desc_live == 1); desc_live--; free(p); }
static void crypto_free_shash(struct crypto_shash *tfm)
{ assert(tfm == &transform && tfm_live == 1 && !desc_live); tfm_live--; frees++; }
static int crypto_shash_digest(struct shash_desc *desc, const unsigned char *input,
                               unsigned int length, unsigned char *output)
{
 static const unsigned char answer[32] = {
  0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
  0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad};
 assert(desc_live == 1 && tfm_live == 1 && desc->tfm == &transform && !desc->flags);
 assert(length == 3 && !memcmp(input, "abc", 3));
 digests++;
 memcpy(output, answer, 32);
 if (scenario == 6) return -EIO; /* Deliberately writes output before failure. */
 if (scenario == 7) output[0] ^= 1;
 return 0;
}
static unsigned int scnprintf(char *buffer, size_t size, const char *format, ...)
{
 int result;
 va_list args;
 va_start(args, format);
 result = vsnprintf(buffer, size, format, args);
 va_end(args);
 assert(result >= 0 && (size_t)result < size);
 return (unsigned int)result;
}
#include "sha256_runtime_kat.c"
int main(int argc, char **argv)
{
 assert(argc == 2);
 scenario = atoi(argv[1]);
 assert(scenario >= 0 && scenario <= 9);
 assert(n10_sha256_kat_init() == 0);
 assert(!tfm_live && !desc_live && allocs == 1 && frees == (scenario != 1));
 assert(digests == (scenario == 0 || scenario == 6 || scenario == 7 || scenario == 8));
 assert(desc_allocs == (scenario == 0 || scenario == 5 || scenario == 6 || scenario == 7 || scenario == 8));
 if (scenario == 8) assert(descriptor_bytes == 4096);
 return 0;
}
