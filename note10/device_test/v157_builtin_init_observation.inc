/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/cred.h>
#include <linux/err.h>
#include <linux/fcntl.h>
#include <linux/fs.h>
#include <linux/namei.h>

void n157_builtin_init_observe(void);

void n157_builtin_init_observe(void)
{
    struct path path;
    struct inode *inode;
    struct file *file;
    unsigned char header[64];
    loff_t position = 0, bytes = -1;
    ssize_t read_count = -ENODATA;
    int lookup_rc, open_rc = -ENODATA, rootfs = 0, regular = 0;
    int elf64le = 0, aarch64 = 0;
    unsigned int execute_bits = 0;

    /* Do not follow a terminal symlink or open a nonregular object. */
    lookup_rc = kern_path("/init", 0, &path);
    if (lookup_rc)
        goto report;

    inode = d_inode(path.dentry);
    rootfs = !strcmp(path.dentry->d_sb->s_type->name, "rootfs");
    if (inode) {
        regular = S_ISREG(inode->i_mode);
        execute_bits = inode->i_mode & S_IXUGO;
    }
    if (!rootfs || !regular)
        goto put_path;

    bytes = i_size_read(inode);
    file = dentry_open(&path, O_RDONLY | O_NONBLOCK | O_NOATIME,
                       current_cred());
    if (IS_ERR(file)) {
        open_rc = (int)PTR_ERR(file);
        goto put_path;
    }
    open_rc = 0;
    read_count = kernel_read(file, header, sizeof(header), &position);
    if (read_count == (ssize_t)sizeof(header)) {
        elf64le = !memcmp(header, "\177ELF\2\1\1", 7);
        aarch64 = elf64le && header[18] == 183 && header[19] == 0;
    }
    filp_close(file, NULL);
put_path:
    path_put(&path);
report:
    printk(KERN_INFO "N157PRE1 id=%s boot=%s cycle=%s lookup=%d rootfs=%d regular=%d open=%d xbits=%o bytes=%lld read=%zd elf64le=%d aarch64=%d\n",
           N154_BUILD_ID, n10_boot_id,
           n10_cycle_valid() ? (const char *)n10_cycle : "00000000000000000000000000000000",
           lookup_rc, rootfs, regular, open_rc, execute_bits,
           (long long)bytes, read_count, elf64le, aarch64);
}
