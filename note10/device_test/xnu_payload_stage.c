/* SPDX-License-Identifier: GPL-2.0-only */
/* Included only in the opt-in same-boot RAM staging diagnostic.
 * Copies a verified experimental XNU memory image into this boot's reservation,
 * reads it back, and stops. It never branches to the payload.
 */
#include <crypto/hash.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/fs.h>
#include <linux/smp.h>
#include <linux/vmalloc.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <asm/memory.h>
#include "note10_xnu_payload_stage.h"

static int n10_sha256(const u8 *data, size_t length, u8 digest[32])
{
    struct crypto_shash *tfm;
    struct shash_desc *desc;
    int error;

    tfm = crypto_alloc_shash("sha256", 0, 0);
    if (IS_ERR(tfm))
        return PTR_ERR(tfm);
    desc = kmalloc(sizeof(*desc) + crypto_shash_descsize(tfm), GFP_KERNEL);
    if (!desc) {
        crypto_free_shash(tfm);
        return -ENOMEM;
    }
    desc->tfm = tfm;
    desc->flags = 0;
    error = crypto_shash_digest(desc, data, length, digest);
    kfree(desc);
    crypto_free_shash(tfm);
    return error;
}

static unsigned int n10_stage_xnu_payload(unsigned long reserved,
                                 unsigned long pages,
                                 unsigned long invalid)
{
    struct file *file;
    loff_t position = 0, file_size;
    u8 digest[32];
    u8 expected[32] = N10_XNU_PAYLOAD_SHA256_BYTES;
    u8 *staging = NULL;
    u8 *destination;
    size_t length = N10_XNU_PAYLOAD_SIZE;
    unsigned int status = 0, sequence;
    char hash[65], frame[256];
    ssize_t count;
    int result, i;
    bool wrote = false;

    if (n10_window_status != 1 || invalid || reserved != pages ||
        pages != (N10_WINDOW_SIZE >> PAGE_SHIFT) ||
        !n10_window_base || (n10_window_base & (N10_WINDOW_ALIGN - 1)) ||
        n10_window_base > N10_WINDOW_LIMIT - N10_WINDOW_SIZE ||
        length == 0 || length > N10_WINDOW_SIZE || length % PAGE_SIZE) {
        status = 1;
        goto report;
    }
    file = filp_open("/xnu/kernel.mem", O_RDONLY, 0);
    if (IS_ERR(file)) {
        status = 2;
        goto report;
    }
    file_size = i_size_read(file_inode(file));
    if (file_size < 0 || (u64)file_size != (u64)length) {
        status = 3;
        filp_close(file, NULL);
        goto report;
    }
    staging = vmalloc(length);
    if (!staging) {
        status = 4;
        filp_close(file, NULL);
        goto report;
    }
    count = kernel_read(file, staging, length, &position);
    filp_close(file, NULL);
    if (count < 0 || (size_t)count != length) {
        status = 5;
        goto report;
    }
    result = n10_sha256(staging, length, digest);
    if (result || memcmp(digest, expected, sizeof(expected))) {
        status = 6;
        goto report;
    }

    destination = phys_to_virt(n10_window_base);
    if (!virt_addr_valid(destination) ||
        virt_to_phys(destination) != n10_window_base ||
        !virt_addr_valid(destination + N10_WINDOW_SIZE - 1) ||
        virt_to_phys(destination + N10_WINDOW_SIZE - 1) !=
            n10_window_base + N10_WINDOW_SIZE - 1) {
        status = 7;
        goto report;
    }
    memset(destination, 0, N10_WINDOW_SIZE);
    memcpy(destination, staging, length);
    wrote = true;
    smp_mb();
    result = n10_sha256(destination, length, digest);
    if (result || memcmp(digest, expected, sizeof(expected))) {
        status = 8;
        goto report;
    }
    if (memchr_inv(destination + length, 0, N10_WINDOW_SIZE - length)) {
        status = 9;
        goto report;
    }
report:
    if (status && wrote) {
        memset(destination, 0, N10_WINDOW_SIZE);
        smp_mb();
    }
    for (i = 0; i < sizeof(digest); ++i)
        snprintf(hash + i * 2, 3, "%02x", status ? 0 : digest[i]);
    hash[64] = '\0';
    for (sequence = 0; sequence < 32; ++sequence) {
        int count = scnprintf(frame, sizeof(frame),
            "id=%s seq=%u base=%llx size=%llx bytes=%llu sha256=%s status=%u",
            N10_RESERVE_BUILD_ID, sequence,
            (unsigned long long)n10_window_base, N10_WINDOW_SIZE,
            (unsigned long long)(status ? 0 : length), hash, status);
        pr_info("N10XNU1 %s checksum=%08x\n", frame,
                n10_frame_checksum(frame, count));
    }
    vfree(staging);
    return status;
}
