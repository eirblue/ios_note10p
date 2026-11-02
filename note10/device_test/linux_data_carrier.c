/* SPDX-License-Identifier: GPL-2.0-only */
/* Opt-in readonly native initrd input; decoded pages are ordinary Linux data. */
#ifndef N10_DATA_HOST_TEST
#include <crypto/hash.h>
#include <linux/err.h>
#include <linux/init.h>
#include <linux/initrd.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/vmalloc.h>
#include <asm/memory.h>
#define n10_data_linear(x) __is_lm_address(x)
#define n10_data_pa(x) __pa(x)
#define n10_data_va(x) ((unsigned long)__va(x))
#define n10_data_alloc(n) vmalloc(n)
#define n10_data_free(p) vfree(p)
#define n10_data_clear(p,n) memzero_explicit(p,n)
#endif
#include "carrier_lzma.h"

enum n10_data_reason {
    N10_DATA_PARAM_MISSING = 1u << 0, N10_DATA_PARAM_INVALID = 1u << 1,
    N10_DATA_PARAM_DUPLICATE = 1u << 2, N10_DATA_CAPTURE_MISSING = 1u << 3,
    N10_DATA_CAPTURE_INVALID = 1u << 4, N10_DATA_CAPTURE_REPEAT = 1u << 5,
    N10_DATA_INPUT_MISSING = 1u << 6, N10_DATA_GLOBAL_MISMATCH = 1u << 7,
    N10_DATA_EMIT_REPEAT = 1u << 8, N10_DATA_STICKY_INVALID = 1u << 9
};

static struct {
    const unsigned char *input;
    unsigned long start, end;
    size_t length;
    unsigned int captures, parameters, invalid, emitted, reasons;
    unsigned char expected[32];
} n10_data;
_Static_assert(sizeof(n10_data) <= 128, "bounded permanent DATA metadata");

static int __init n10_data_parameter(char *value)
{
    unsigned char parsed[32];
    unsigned int i;
    if (n10_data.parameters++) { n10_data.invalid = 1; n10_data.reasons |= N10_DATA_PARAM_DUPLICATE; return 1; }
    for (i = 0; i < 64; ++i) {
        unsigned int digit;
        if (!value[i]) { n10_data.invalid = 1; n10_data.reasons |= N10_DATA_PARAM_INVALID; return 1; }
        if (value[i] >= '0' && value[i] <= '9') digit = value[i]-'0';
        else if (value[i] >= 'a' && value[i] <= 'f') digit = value[i]-'a'+10;
        else { n10_data.invalid = 1; n10_data.reasons |= N10_DATA_PARAM_INVALID; return 1; }
        if (!(i & 1)) parsed[i/2] = digit << 4;
        else parsed[i/2] |= digit;
    }
    if (value[64]) { n10_data.invalid = 1; n10_data.reasons |= N10_DATA_PARAM_INVALID; return 1; }
    memcpy(n10_data.expected, parsed, sizeof(parsed));
    n10_data_clear(parsed, sizeof(parsed));
    return 1;
}
#ifndef N10_DATA_HOST_TEST
__setup("n10.data_sha=", n10_data_parameter);
#endif

void __init n10_data_capture(unsigned long start, unsigned long end);
void __init n10_data_capture(unsigned long start, unsigned long end)
{
    unsigned long length;
    uint64_t physical;
    if (n10_data.captures++) { n10_data.invalid = 1; n10_data.reasons |= N10_DATA_CAPTURE_REPEAT; return; }
    if (!start || end <= start) { n10_data.invalid = 1; n10_data.reasons |= N10_DATA_CAPTURE_INVALID; return; }
    length = end-start;
    if (length <= 128 || length > N10_LZMA_MAX_BYTES ||
        !n10_data_linear(start) || !n10_data_linear(end-1)) {
        n10_data.invalid = 1; n10_data.reasons |= N10_DATA_CAPTURE_INVALID; return;
    }
    physical = n10_data_pa(start);
    if (physical > UINT64_MAX-length || n10_data_va(physical) != start ||
        n10_data_pa(end-1) != physical+length-1) {
        n10_data.invalid = 1; n10_data.reasons |= N10_DATA_CAPTURE_INVALID; return;
    }
    n10_data.input = (const unsigned char *)start;
    n10_data.start = start; n10_data.end = end; n10_data.length = length;
}

static uint64_t n10_data_le(const unsigned char *p, unsigned int bytes)
{
    uint64_t value = 0;
    unsigned int i;
    for (i = 0; i < bytes; ++i) value |= (uint64_t)p[i] << (8*i);
    return value;
}

#ifndef N10_DATA_HOST_TEST
static int n10_data_hash(const void *data, size_t bytes, unsigned char digest[32])
{
    struct crypto_shash *tfm;
    struct shash_desc *desc = NULL;
    unsigned int size;
    int error;
    tfm = crypto_alloc_shash("sha256-generic", 0, 0);
    if (IS_ERR(tfm)) return PTR_ERR(tfm);
    if (strcmp(crypto_shash_driver_name(tfm), "sha256-generic") || crypto_shash_digestsize(tfm) != 32) {
        error = -EINVAL; goto out;
    }
    size = crypto_shash_descsize(tfm);
    if (size > 4096-sizeof(*desc)) { error = -E2BIG; goto out; }
    desc = kzalloc(sizeof(*desc)+size, GFP_KERNEL);
    if (!desc) { error = -ENOMEM; goto out; }
    desc->tfm = tfm; desc->flags = 0;
    error = crypto_shash_digest(desc, data, bytes, digest);
    n10_data_clear(desc, sizeof(*desc)+size);
    kfree(desc);
out:
    crypto_free_shash(tfm);
    return error;
}
#endif

struct n10_data_outcome {
    const char *status;
    uint64_t carrier, stream, payload, consumed, written;
    unsigned int decoded, reasons, parameters, captures, retained;
    unsigned char digest[32];
};

static void n10_data_run(struct n10_data_outcome *out)
{
    const unsigned char *p = n10_data.input;
    unsigned char digest[32] = {0};
    unsigned char *output = NULL;
    void *workspace = NULL;
    uint64_t count, payload;
    size_t i;
    struct n10_lzma_result result = {0};
    int status;
    memset(out, 0, sizeof(*out)); out->status = "unavailable";
    out->reasons = n10_data.reasons;
    out->parameters = n10_data.parameters > 1 ? 2 : n10_data.parameters;
    out->captures = n10_data.captures > 1 ? 2 : n10_data.captures;
    out->retained = p != NULL;
    if (!n10_data.parameters) out->reasons |= N10_DATA_PARAM_MISSING;
    if (!n10_data.captures) out->reasons |= N10_DATA_CAPTURE_MISSING;
    if (!p) out->reasons |= N10_DATA_INPUT_MISSING;
    if (initrd_start != n10_data.start || initrd_end != n10_data.end) out->reasons |= N10_DATA_GLOBAL_MISMATCH;
    if (n10_data.emitted) out->reasons |= N10_DATA_EMIT_REPEAT;
    if (n10_data.invalid) out->reasons |= N10_DATA_STICKY_INVALID;
    if (n10_data.emitted++ || n10_data.invalid || n10_data.captures != 1 ||
        n10_data.parameters != 1 || !p || initrd_start != n10_data.start || initrd_end != n10_data.end)
        return;
    out->carrier = n10_data.length;
    out->status = "carrier_hash";
    if (n10_data_hash(p, n10_data.length, digest) || memcmp(digest,n10_data.expected,32)) goto done;
    out->status = "header";
    if (memcmp(p,"N10DATA1",8) || n10_data_le(p+8,2) != 1 || n10_data_le(p+10,2) != 128 ||
        n10_data_le(p+12,4) || n10_data_le(p+16,8) != n10_data.length || n10_data_le(p+24,8) != 128)
        goto done;
    count = n10_data_le(p+32,8); payload = n10_data_le(p+40,8);
    if (count < 18 || count > n10_data.length-128 || !payload || payload > N10_LZMA_MAX_BYTES) goto done;
    for (i = 112; i < 128; ++i) if (p[i]) goto done;
    for (i = 128+(size_t)count; i < n10_data.length; ++i) if (p[i]) goto done;
    if (p[128] != 0x5d || n10_data_le(p+129,4) != (1u << 23) || n10_data_le(p+133,8) != payload) goto done;
    out->stream = count; out->payload = payload;
    out->status = "stream_hash";
    if (n10_data_hash(p+128,count,digest) || memcmp(digest,p+48,32)) goto done;
    out->status = "allocation";
    output = n10_data_alloc((size_t)payload);
    workspace = n10_data_alloc(N10_LZMA_WORKSPACE);
    if (!output || !workspace) goto done;
    out->status = "decode";
    out->decoded = 1;
    status = n10_lzma_alone_decode(p+128,(size_t)count,output,(size_t)payload,
        workspace,N10_LZMA_WORKSPACE,&result);
    out->consumed = result.consumed; out->written = result.written;
    if (status || result.version != 1 || result.status || result.written != payload || result.consumed > count) goto done;
    out->status = "payload_hash";
    if (n10_data_hash(output,payload,digest) || memcmp(digest,p+80,32)) goto done;
    memcpy(out->digest,digest,32); out->status = "ok";
done:
    if (workspace) { n10_data_clear(workspace,N10_LZMA_WORKSPACE); n10_data_free(workspace); }
    if (output) { n10_data_clear(output,(size_t)out->payload); n10_data_free(output); }
    n10_data_clear(digest,sizeof(digest));
}

#ifndef N10_DATA_HOST_TEST
static int n10_data_emit(void)
{
    struct n10_data_outcome outcome;
    char frame[384], digest[65];
    unsigned int i;
    int count;
    static const char digits[] = "0123456789abcdef";
    n10_data_run(&outcome);
    for (i = 0; i < 32; ++i) { digest[2*i] = digits[outcome.digest[i] >> 4]; digest[2*i+1] = digits[outcome.digest[i]&15]; }
    digest[64] = 0;
    count = scnprintf(frame,sizeof(frame),
        "id=%s cycle=%s kind=result status=%s carrier=%llu stream=%llu payload=%llu consumed=%llu written=%llu calls=%u digest=%s reasons=%08x params=%u captures=%u retained=%u ownership=0 executed=0",
        N10_SHA256_KAT_ID,(const char *)n10_cycle,outcome.status,
        (unsigned long long)outcome.carrier,(unsigned long long)outcome.stream,(unsigned long long)outcome.payload,
        (unsigned long long)outcome.consumed,(unsigned long long)outcome.written,outcome.decoded,digest,outcome.reasons,outcome.parameters,outcome.captures,outcome.retained);
    pr_info("N10DATA1 %s checksum=%08x\n",frame,n10_frame_checksum(frame,count));
    n10_data_clear(&outcome,sizeof(outcome)); n10_data_clear(digest,sizeof(digest));
    return 0;
}
#endif
