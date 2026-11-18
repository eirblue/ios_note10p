/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after initramfs globals; probes run before deferred free_initmem. */
#ifndef N297_HOST_TEST
#include <linux/namei.h>
#include <linux/dcache.h>
#include "../drivers/misc/v154_linux_id.h"
#endif
#define N297_SLOT_BYTES 10962166UL
#define N297_PRE 1U
#define N297_POST 2U
#define N297_LATE 4U
#define N297_HASHED 8U
struct n297_observation {
    unsigned int flags, hash_stage, open_seen;
    unsigned long hash_declared;
    u32 magic, fnv;
    int unpack_rc, open_rc;
};
void __init n297_rootfs_final_probe(void);
static struct n297_observation __initdata n297_observed = {
    .unpack_rc = -EINPROGRESS, .open_rc = -EINPROGRESS,
};

static void __init n297_capture_once(unsigned int stage)
{
    const unsigned char *data = (const unsigned char *)__initramfs_start;
    unsigned long index;
    u32 value = 2166136261U;
    if (n297_observed.flags & N297_HASHED)
        return;
    /* This exact linked slot is independently bounded by the producer. No
     * runtime size or caller-supplied pointer controls the memory read. */
    for (index = 0; index < N297_SLOT_BYTES; ++index)
        value = (value ^ data[index]) * 16777619U;
    n297_observed.magic = (u32)data[0] | (u32)data[1] << 8 |
                          (u32)data[2] << 16 | (u32)data[3] << 24;
    n297_observed.fnv = value;
    n297_observed.hash_declared = __initramfs_size;
    n297_observed.hash_stage = stage;
    n297_observed.flags |= N297_HASHED;
}

static int __init n297_lookup(const char *name, unsigned long *ino,
        unsigned int *mode, long long *size, unsigned long *magic)
{
    struct path path;
    int result = kern_path(name, LOOKUP_FOLLOW, &path);
    if (!result) {
        struct inode *inode = d_inode(path.dentry);
        *ino = inode->i_ino;
        *mode = inode->i_mode;
        *size = (long long)i_size_read(inode);
        *magic = inode->i_sb->s_magic;
        path_put(&path);
    }
    return result;
}

static void __init n297_report(const char *stage)
{
    unsigned long ino = 0, magic = 0, root_ino = 0, root_magic = 0;
    unsigned long console_ino = 0, console_magic = 0;
    unsigned int mode = 0, root_mode = 0, console_mode = 0;
    long long size = -1, root_size = -1, console_size = -1;
    int init_rc = n297_lookup("/init", &ino, &mode, &size, &magic);
    int console_rc = n297_lookup("/dev/console", &console_ino,
                                &console_mode, &console_size, &console_magic);
    int root_rc = n297_lookup("/", &root_ino, &root_mode,
                             &root_size, &root_magic);
    pr_info("N297RFS id=%s stage=%s flags=%u declared=%lu hash_declared=%lu span=%lu magic=%08x fnv=%08x hash_stage=%u skip=%d unpack=%d open_seen=%u open_rc=%d init_rc=%d mode=%u ino=%lu size=%lld console_rc=%d root_rc=%d root_magic=%lu root_ino=%lu\n",
        N154_BUILD_ID, stage, n297_observed.flags, __initramfs_size,
        n297_observed.hash_declared, N297_SLOT_BYTES, n297_observed.magic,
        n297_observed.fnv, n297_observed.hash_stage, do_skip_initramfs,
        n297_observed.unpack_rc, n297_observed.open_seen,
        n297_observed.open_rc, init_rc, mode, ino, size,
        console_rc, root_rc, root_magic, root_ino);
}

static void __init n297_note_init_open(const char *name, int result)
{
    if (!strcmp(name, "init")) {
        ++n297_observed.open_seen;
        n297_observed.open_rc = result;
    }
}
static void __init n297_before_unpack(void)
{
    n297_observed.flags |= N297_PRE;
    n297_capture_once(1);
    n297_report("pre");
}
static void __init n297_after_unpack(int result)
{
    n297_observed.flags |= N297_POST;
    n297_observed.unpack_rc = result;
    n297_report("post");
}
void __init n297_rootfs_final_probe(void)
{
    n297_observed.flags |= N297_LATE;
    n297_capture_once(3); /* Still works if populate_rootfs never ran. */
    n297_report("late");
}
