/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_ROOTFS_SNAPSHOT_H
#define NOTE10_ROOTFS_SNAPSHOT_H

struct n159_rootfs_snapshot {
    unsigned long declared_size;
    unsigned int populate_seen;
    unsigned int skip;
    unsigned int init_members;
    int init_open_result;
};

/* Permanent storage/accessor: pre-exec can run after free_initmem(). */
void n159_rootfs_get_snapshot(struct n159_rootfs_snapshot *out);

#endif
