/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual probe code with synthetic RAM and VFS; no worker/hardware execution. */
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define N297_HOST_TEST 1
#define __init
#define __initdata
#define LOOKUP_FOLLOW 1
#define N154_BUILD_ID "11111111111111111111111111111111"
typedef uint32_t u32;
static char __initramfs_start[10962166];
static unsigned long __initramfs_size = sizeof(__initramfs_start);
static int do_skip_initramfs, init_present, lines;
static char last_line[1024];
struct super_block { unsigned long s_magic; };
struct inode { unsigned long i_ino; unsigned int i_mode; long long size; struct super_block *i_sb; };
struct dentry { struct inode *inode; };
struct path { struct dentry *dentry; };
static struct super_block sb = { 0x858458f6UL };
static struct inode init_inode = { 7, 0100750, 2146400, &sb };
static struct inode root_inode = { 1, 0040755, 0, &sb };
static struct dentry init_entry = { &init_inode }, root_entry = { &root_inode };
static int kern_path(const char *name, unsigned int flags, struct path *path)
{
    (void)flags;
    if (!strcmp(name, "/")) { path->dentry = &root_entry; return 0; }
    if (!strcmp(name, "/init") && init_present) { path->dentry = &init_entry; return 0; }
    return -ENOENT;
}
static struct inode *d_inode(struct dentry *entry) { return entry->inode; }
static long long i_size_read(const struct inode *inode) { return inode->size; }
static void path_put(struct path *path) { (void)path; }
static int record_line(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    int result = vsnprintf(last_line, sizeof(last_line), format, args);
    va_end(args);
    assert(result > 0 && (unsigned int)result < sizeof(last_line));
    assert(strstr(last_line, "N297RFS id=" N154_BUILD_ID));
    ++lines;
    return result;
}
#define pr_info record_line
#include "v297_rootfs_probe.inc"
static void reset_probe(void)
{
    n297_observed = (struct n297_observation){ .unpack_rc = -EINPROGRESS, .open_rc = -EINPROGRESS };
    init_present = lines = do_skip_initramfs = 0;
    __initramfs_start[0] = 0;
}
int main(void)
{
    n297_rootfs_final_probe();
    assert(n297_observed.flags == 12 && n297_observed.hash_stage == 3 && n297_observed.fnv == 0x5ed99a5dU);
    assert(n297_observed.open_seen == 0 && n297_observed.unpack_rc == -EINPROGRESS);
    assert(strstr(last_line, "stage=late") && strstr(last_line, "init_rc=-2"));
    assert(lines == 1);

    reset_probe();
    n297_before_unpack();
    u32 before = n297_observed.fnv;
    __initramfs_start[0] = 1; /* Prove later reports never rehash the slot. */
    n297_note_init_open("other", -1);
    n297_note_init_open("init", 0);
    init_present = 1;
    n297_after_unpack(0);
    n297_rootfs_final_probe();
    assert(n297_observed.flags == 15 && n297_observed.hash_stage == 1);
    assert(n297_observed.fnv == before && n297_observed.open_seen == 1);
    assert(strstr(last_line, "init_rc=0") && strstr(last_line, "size=2146400"));
    assert(lines == 3);

    reset_probe();
    n297_before_unpack();
    n297_note_init_open("init", -EACCES);
    n297_after_unpack(0);
    n297_rootfs_final_probe();
    assert(n297_observed.flags == 15 && n297_observed.unpack_rc == 0);
    assert(n297_observed.open_seen == 1 && n297_observed.open_rc == -EACCES);
    assert(strstr(last_line, "init_rc=-2") && strstr(last_line, "open_rc=-13"));
    assert(lines == 3);
    puts("{\"passed\":true,\"groups\":1,\"variants\":3,\"assertions\":12}");
    return 0;
}
