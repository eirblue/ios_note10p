/* SPDX-License-Identifier: GPL-2.0-only */
/* New messages only. Opaque state never leaves this provider/boot. */
#ifndef N10_STREAM_HOST_TEST
#include <crypto/hash.h>
#include <linux/err.h>
#include <linux/errno.h>
#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/string.h>
#endif
#include "note10_sha256_kat_id.h"
#include "sha256_stream_vectors.h"

struct n10_stream_result {
    int status;
    unsigned int streamed, exported, imported, resumed;
    unsigned char direct[32], restored[32];
};

static void n10_stream_case(struct shash_desc *a, struct shash_desc *b,
                           unsigned char *state, const unsigned char *message,
                           const struct n10_stream_vector *v,
                           struct n10_stream_result *r)
{
    int status;
    memset(r, 0, sizeof(*r));
    status = crypto_shash_init(a);
    if (status) goto done;
    status = crypto_shash_update(a, message, 1);
    if (status) goto done;
    status = crypto_shash_update(a, message+1, 54);
    if (status) goto done;
    /* Includes a zero-length update for the new length55 message. */
    status = crypto_shash_update(a, message+55, v->length-55);
    if (status) goto done;
    status = crypto_shash_final(a, r->direct);
    if (status) { memset(r->direct, 0, 32); goto done; }
    r->streamed = 1;
    if (memcmp(r->direct, v->answer, 32)) { status = -EBADMSG; goto done; }
    status = crypto_shash_init(a);
    if (status) goto done;
    status = crypto_shash_update(a, message, v->split);
    if (status) goto done;
    status = crypto_shash_export(a, state);
    if (status) goto done;
    r->exported = 1;
    /* A distinct descriptor on the SAME tfm. Never deserialize into a new
     * driver/kernel, expose raw state, or infer a portable state layout. */
    status = crypto_shash_init(b);
    if (status) goto done;
    status = crypto_shash_import(b, state);
    if (status) goto done;
    r->imported = 1;
    status = crypto_shash_update(b, message+v->split, v->length-v->split);
    if (status) goto done;
    status = crypto_shash_final(b, r->restored);
    if (status) { memset(r->restored, 0, 32); goto done; }
    r->resumed = 1;
    if (memcmp(r->restored, v->answer, 32)) status = -EBADMSG;
done:
    r->status = status;
}

static void n10_stream_hex(char out[65], const unsigned char in[32])
{
    static const char digits[] = "0123456789abcdef";
    unsigned int i;
    for (i = 0; i < 32; ++i) {
        out[2*i] = digits[in[i] >> 4];
        out[2*i+1] = digits[in[i] & 15];
    }
    out[64] = 0;
}

static int n10_sha256_stream_init(void)
{
    struct crypto_shash *tfm;
    struct shash_desc *a = NULL, *b = NULL;
    unsigned char *state = NULL, message[129];
    unsigned int descsize, statesize = 0, i, copy, length;
    int status;
    unsigned int driver = 0;
    struct n10_stream_result r;
    char direct[65], restored[65], frame[512];

    for (i = 0; i < sizeof(message); ++i) message[i] = (37*i+11) & 255;
    /* These synchronous calls are NOT hard-cancellable. The unchanged
     * recovery worker owns a separate non-freezable queue. */
    tfm = crypto_alloc_shash("sha256-generic", 0, 0);
    if (IS_ERR(tfm)) { status = PTR_ERR(tfm); goto frames; }
    status = -EINVAL;
    if (strcmp(crypto_shash_driver_name(tfm), "sha256-generic")) goto frames;
    driver = 1;
    if (crypto_shash_digestsize(tfm) != 32) goto frames;
    descsize = crypto_shash_descsize(tfm);
    statesize = crypto_shash_statesize(tfm);
    status = -E2BIG;
    if (!statesize || statesize > 4096 || sizeof(*a) > 4096 || descsize > 4096-sizeof(*a)) goto frames;
    a = kzalloc(sizeof(*a)+descsize, GFP_KERNEL);
    b = kzalloc(sizeof(*b)+descsize, GFP_KERNEL);
    state = kzalloc(statesize, GFP_KERNEL);
    status = -ENOMEM;
    if (!a || !b || !state) goto frames;
    a->tfm = b->tfm = tfm;
    a->flags = b->flags = 0;
    status = 0;
frames:
    for (i = 0; i < ARRAY_SIZE(n10_stream_vectors); ++i) {
        memset(&r, 0, sizeof(r));
        r.status = status;
        if (!status) n10_stream_case(a, b, state, message, &n10_stream_vectors[i], &r);
        n10_stream_hex(direct, r.direct); n10_stream_hex(restored, r.restored);
        for (copy = 0; copy < 2; ++copy) {
            length = scnprintf(frame, sizeof(frame),
                "id=%s cycle=%s case=%u copy=%u len=%u split=%u statesize=%u status=%d driver_match=%u streamed=%u exported=%u imported=%u resumed=%u direct=%s restored=%s",
                N10_SHA256_KAT_ID, (const char *)n10_cycle, i, copy,
                n10_stream_vectors[i].length, n10_stream_vectors[i].split, statesize,
                r.status, driver, r.streamed, r.exported, r.imported, r.resumed, direct, restored);
            pr_info("N10SHASTREAM1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, length));
        }
    }
    kfree(state); kfree(b); kfree(a);
    if (!IS_ERR(tfm)) crypto_free_shash(tfm);
    return 0; /* Observation failure never blocks recovery initialization. */
}
