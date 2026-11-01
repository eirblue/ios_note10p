/* NEW protocol/body fixture, OpenSSL host state only; not Linux execution. */
#include <openssl/sha.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define N10_STREAM_HOST_TEST
#define GFP_KERNEL 0
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define kzalloc(n, f) calloc(1, (n))
#define kfree free
#define IS_ERR(p) 0
#define PTR_ERR(p) ((int)(long)(p))
struct crypto_shash { int dummy; };
struct shash_desc { struct crypto_shash *tfm; unsigned int flags; };
static struct crypto_shash transform;
static const char *scenario;
static unsigned int exports, imports, finals;
static char n10_cycle[] = "22222222222222222222222222222222";
static struct crypto_shash *crypto_alloc_shash(const char *name, int a, int b)
{
    (void)a; (void)b;
    if (strcmp(name, "sha256-generic")) exit(90);
    return &transform;
}
static void crypto_free_shash(struct crypto_shash *tfm) { if (tfm != &transform) exit(91); }
static const char *crypto_shash_driver_name(struct crypto_shash *tfm) { (void)tfm; return "sha256-generic"; }
static unsigned int crypto_shash_digestsize(struct crypto_shash *tfm) { (void)tfm; return 32; }
static unsigned int crypto_shash_descsize(struct crypto_shash *tfm) { (void)tfm; return sizeof(SHA256_CTX); }
static unsigned int crypto_shash_statesize(struct crypto_shash *tfm)
{ (void)tfm; return !strcmp(scenario, "state-bound") ? 4097 : sizeof(SHA256_CTX); }
static SHA256_CTX *context(struct shash_desc *desc) { return (SHA256_CTX *)(desc+1); }
static int crypto_shash_init(struct shash_desc *desc) { return SHA256_Init(context(desc)) ? 0 : -EIO; }
static int crypto_shash_update(struct shash_desc *desc, const unsigned char *data, unsigned int n)
{ return SHA256_Update(context(desc), data, n) ? 0 : -EIO; }
static int crypto_shash_final(struct shash_desc *desc, unsigned char *out)
{
    int status = SHA256_Final(out, context(desc)) ? 0 : -EIO;
    if (++finals == 5 && !strcmp(scenario, "digest-mismatch")) out[0] ^= 1;
    return status;
}
static int crypto_shash_export(struct shash_desc *desc, void *state)
{
    if (++exports == 3 && !strcmp(scenario, "export-error")) return -EIO;
    memcpy(state, context(desc), sizeof(SHA256_CTX)); return 0;
}
static int crypto_shash_import(struct shash_desc *desc, const void *state)
{
    if (++imports == 4 && !strcmp(scenario, "import-error")) return -EIO;
    memcpy(context(desc), state, sizeof(SHA256_CTX)); return 0;
}
static unsigned int n10_frame_checksum(const char *text, unsigned int length)
{
    unsigned int value = 2166136261U, i;
    for (i = 0; i < length; ++i) value = (value ^ (unsigned char)text[i])*16777619U;
    return value;
}
static int scnprintf(char *p, size_t n, const char *fmt, ...)
{
    int result; va_list ap;
    va_start(ap, fmt); result = vsnprintf(p, n, fmt, ap); va_end(ap);
    return result < (int)n ? result : (int)n-1;
}
#define pr_info(fmt, ...) printf("N10BOOTLINK2 boot=33333333333333333333333333333333 " fmt, ##__VA_ARGS__)
#include "sha256_stream_state.c"
int main(int argc, char **argv)
{
    if (argc != 2) return 92;
    scenario = argv[1];
    return n10_sha256_stream_init();
}
