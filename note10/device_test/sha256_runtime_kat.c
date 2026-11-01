/* SPDX-License-Identifier: GPL-2.0-only */
/* Opt-in Linux crypto prerequisite. No reserved RAM, PM or XNU execution. */
#ifdef N10_SHA256_KAT_HOST_TEST
#include "sha256_kat_host.h"
#else
#include <crypto/hash.h>
#include <linux/err.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/string.h>
#endif
#include "note10_sha256_kat_id.h"

static const unsigned char n10_sha256_answer[32] = {
 0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
 0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad
};

static unsigned int n10_sha256_frame_checksum(const char *text, unsigned int size)
{
 unsigned int value = 2166136261U, i;
 for (i = 0; i < size; i++) value = (value ^ (unsigned char)text[i]) * 16777619U;
 return value;
}

static int __init n10_sha256_kat_init(void)
{
 struct crypto_shash *tfm;
 struct shash_desc *desc = NULL;
 unsigned char digest[32] = {0};
 char hex[65], frame[320];
 unsigned int context_size, i, copy, length;
 int status, driver_match = 0, computed = 0;

 /* Allocation/digest are synchronous and have no hard local time bound.
  * This remains default-off until recovery integration is independently gated. */
 tfm = crypto_alloc_shash("sha256-generic", 0, 0);
 if (IS_ERR(tfm)) { status = PTR_ERR(tfm); goto frames; }
 status = -EINVAL;
 if (strcmp(crypto_shash_driver_name(tfm), "sha256-generic")) goto free_tfm;
 driver_match = 1;
 if (crypto_shash_digestsize(tfm) != sizeof(digest)) goto free_tfm;
 context_size = crypto_shash_descsize(tfm);
 /* Fixed byte ceiling, independent of page size; subtraction prevents overflow. */
 if (sizeof(*desc) > 4096 || context_size > 4096 - sizeof(*desc)) goto free_tfm;
 desc = kzalloc(sizeof(*desc) + context_size, GFP_KERNEL);
 status = -ENOMEM;
 if (!desc) goto free_tfm;
 desc->tfm = tfm;
 desc->flags = 0;
 status = crypto_shash_digest(desc, (const unsigned char *)"abc", 3, digest);
 if (!status) {
  computed = 1;
  if (memcmp(digest, n10_sha256_answer, sizeof(digest))) status = -EBADMSG;
 } else {
  /* Failed callbacks may leave partial output; never publish it as a digest. */
  memset(digest, 0, sizeof(digest));
 }
 kfree(desc);
free_tfm:
 crypto_free_shash(tfm);
frames:
 for (i = 0; i < sizeof(digest); i++) {
  static const char digits[] = "0123456789abcdef";
  hex[2*i] = digits[digest[i] >> 4];
  hex[2*i+1] = digits[digest[i] & 15];
 }
 hex[64] = 0;
 for (copy = 0; copy < 2; copy++) {
  length = scnprintf(frame, sizeof(frame),
   "id=%s copy=%u phase=late-init status=%d driver_match=%d computed=%d digest=%s",
   N10_SHA256_KAT_ID, copy, status, driver_match, computed, hex);
  pr_info("N10SHA1 %s checksum=%08x\n", frame, n10_sha256_frame_checksum(frame, length));
 }
 /* A failed observation must not prevent Linux/recovery initialization. */
 return 0;
}
late_initcall(n10_sha256_kat_init);
