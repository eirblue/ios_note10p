/* SPDX-License-Identifier: GPL-2.0-only */
/* Current flat bytes after paging/reservations; never pristine firmware. */
#ifndef N10_FDT_HOST_TEST
#include <crypto/hash.h>
#include <linux/bootmem.h>
#include <linux/mm.h>
#include <linux/err.h>
#include <linux/errno.h>
#include <linux/init.h>
#include <linux/slab.h>
#include <linux/string.h>
#endif
#define N10_FDT_CAPACITY (512U * 1024U)
#define N10_FDT_HEADER 40U
/* Owned memblock pages stay reserved through reboot; only tiny state in BSS. */
static unsigned char *n10_fdt_snapshot;
static unsigned int n10_fdt_length, n10_fdt_allocated, n10_fdt_attempted;
static const char *n10_fdt_status = "unavailable";

void __init n10_post_paging_fdt_capture(const void *params, unsigned int length);
void __init n10_post_paging_fdt_capture(const void *params, unsigned int length)
{
    if (n10_fdt_attempted) {
        n10_fdt_status = "ambiguous";
        return;
    }
    n10_fdt_attempted = 1;
    if (!params || length < N10_FDT_HEADER || length > N10_FDT_CAPACITY) {
        n10_fdt_status = "refused";
        return;
    }
    /* Supported pre-slab boundary: kernel/initrd/FDT reservations and mappings
     * already exist. Ordinary allocation failure affects this diagnostic only. */
    n10_fdt_allocated = PAGE_ALIGN(length);
    n10_fdt_snapshot = memblock_virt_alloc_nopanic(n10_fdt_allocated, PAGE_SIZE);
    if (!n10_fdt_snapshot) {
        n10_fdt_allocated = 0;
        return; /* Keep unavailable; never alter Linux admission. */
    }
    memcpy(n10_fdt_snapshot, params, length);
    n10_fdt_length = length;
    n10_fdt_status = "captured";
}

static int n10_fdt_binding_init(void)
{
    struct crypto_shash *tfm = NULL;
    struct shash_desc *desc = NULL;
    unsigned int descsize, length = 0, i;
    unsigned char digest[32] = {0};
    char hex[65], frame[384];
    const char *status = n10_fdt_status;
    int error = 0, count;
    static const char digits[] = "0123456789abcdef";

    /* Called ONLY by the unchanged admitted worker after recovery is armed.
     * A synchronous crypto call still has no hard cancellation guarantee. */
    if (!strcmp(status, "captured")) {
        tfm = crypto_alloc_shash("sha256-generic", 0, 0);
        if (IS_ERR(tfm)) { error = PTR_ERR(tfm); tfm = NULL; goto failed; }
        if (strcmp(crypto_shash_driver_name(tfm), "sha256-generic") ||
            crypto_shash_digestsize(tfm) != sizeof(digest)) {
            error = -EINVAL; goto failed;
        }
        descsize = crypto_shash_descsize(tfm);
        if (sizeof(*desc) > 4096 || descsize > 4096 - sizeof(*desc)) {
            error = -E2BIG; goto failed;
        }
        desc = kzalloc(sizeof(*desc) + descsize, GFP_KERNEL);
        if (!desc) { error = -ENOMEM; goto failed; }
        desc->tfm = tfm;
        desc->flags = 0;
        error = crypto_shash_digest(desc, n10_fdt_snapshot, n10_fdt_length, digest);
        if (error) goto failed;
        length = n10_fdt_length;
        status = "ok";
        goto emit;
failed:
        status = "hash_error";
        memzero_explicit(digest, sizeof(digest));
    }
emit:
    if (desc) { memzero_explicit(desc, sizeof(*desc) + descsize); kfree(desc); }
    if (tfm) crypto_free_shash(tfm);
    /* Clear padding too. Memblock pages remain reserved; NEVER kfree here. */
    if (n10_fdt_snapshot)
        memzero_explicit(n10_fdt_snapshot, n10_fdt_allocated);
    n10_fdt_length = 0;
    n10_fdt_status = "unavailable";
    if (length) {
        for (i = 0; i < sizeof(digest); ++i) {
            hex[2*i] = digits[digest[i] >> 4];
            hex[2*i+1] = digits[digest[i] & 15];
        }
        hex[64] = 0;
    } else {
        memcpy(hex, "none", 5);
    }
    count = scnprintf(frame, sizeof(frame),
        "id=%s cycle=%s boundary=post_paging_reservations status=%s error=%d length=%u sha256=%s raw_binding=0",
        N10_SHA256_KAT_ID, (const char *)n10_cycle, status, error, length, hex);
    pr_info("N10FDT1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    memzero_explicit(digest, sizeof(digest));
    return 0; /* Capture/hash failure never changes Linux admission/recovery. */
}
