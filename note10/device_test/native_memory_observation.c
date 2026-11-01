/* SPDX-License-Identifier: GPL-2.0-only */
/* Existing native nonzero decoded arguments; no successful-addition claim. */
#ifndef N10_MEMORY_HOST_TEST
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/types.h>
#endif
#define N10_MEMORY_CAPACITY 16U
#define N10_MEMORY_OVERFLOW 1U
#define N10_MEMORY_REPEAT 2U
#define N10_MEMORY_WIDTH 4U
#define N10_MEMORY_SATURATED 8U
#define N10_MEMORY_NO_BLOB 16U
#define N10_MEMORY_EXIT 32U
#define N10_MEMORY_NO_END 64U
struct n10_memory_row { u64 base, size; u32 flags, ordinal; };
static struct {
    struct n10_memory_row rows[N10_MEMORY_CAPACITY];
    u32 seen, stored, dropped;
    int address_cells, size_cells, offset, depth, rc;
    u32 attempted, active, ended, flags;
} n10_memory __used;

void __init n10_memory_begin(int address_cells, int size_cells);
void __init n10_memory_row(u64 base, u64 size, u32 flags);
void __init n10_memory_end(int missing_blob, int offset, int depth, int rc);
void __init n10_memory_begin(int address_cells, int size_cells)
{
    BUILD_BUG_ON(sizeof(n10_memory) > 512);
    if (n10_memory.attempted) {
        n10_memory.flags |= N10_MEMORY_REPEAT;
        n10_memory.active = 0;
        return;
    }
    n10_memory.attempted = n10_memory.active = 1;
    n10_memory.address_cells = address_cells;
    n10_memory.size_cells = size_cells;
    if ((address_cells != 1 && address_cells != 2) ||
        (size_cells != 1 && size_cells != 2))
        n10_memory.flags |= N10_MEMORY_WIDTH;
}
void __init n10_memory_row(u64 base, u64 size, u32 flags)
{
    struct n10_memory_row *row;
    u32 ordinal;
    if (!n10_memory.active || !size)
        return;
    if (n10_memory.seen == ~0U) {
        n10_memory.flags |= N10_MEMORY_SATURATED;
        return;
    }
    ordinal = n10_memory.seen++;
    if (n10_memory.stored == N10_MEMORY_CAPACITY) {
        n10_memory.flags |= N10_MEMORY_OVERFLOW;
        if (n10_memory.dropped == ~0U)
            n10_memory.flags |= N10_MEMORY_SATURATED;
        else
            ++n10_memory.dropped;
        return;
    }
    row = &n10_memory.rows[n10_memory.stored++];
    row->base = base; row->size = size; row->flags = flags; row->ordinal = ordinal;
}
void __init n10_memory_end(int missing_blob, int offset, int depth, int rc)
{
    if (!n10_memory.active)
        return;
    n10_memory.active = 0; n10_memory.ended = 1;
    n10_memory.offset = offset; n10_memory.depth = depth; n10_memory.rc = rc;
    if (missing_blob)
        n10_memory.flags |= N10_MEMORY_NO_BLOB;
    else if (rc || offset < 0 || depth >= 0)
        n10_memory.flags |= N10_MEMORY_EXIT;
}
static int n10_memory_emit(void)
{
    char frame[384];
    unsigned int i, flags = n10_memory.flags;
    unsigned int complete;
    int count;
    if (!n10_memory.attempted || !n10_memory.ended || n10_memory.active)
        flags |= N10_MEMORY_NO_END;
    complete = !flags && n10_memory.attempted && n10_memory.ended &&
        !n10_memory.active && !n10_memory.rc && n10_memory.offset >= 0 && n10_memory.depth < 0;
    count = scnprintf(frame, sizeof(frame),
        "id=%s cycle=%s kind=begin stage=native_linux_memory_scan_nonzero_add_arguments ac=%d sc=%d capacity=16 attempted=%u raw_binding=0",
        N10_SHA256_KAT_ID, (const char *)n10_cycle, n10_memory.address_cells,
        n10_memory.size_cells, n10_memory.attempted);
    pr_info("N10MEMARGS1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    for (i = 0; i < n10_memory.stored; ++i) {
        const struct n10_memory_row *row = &n10_memory.rows[i];
        count = scnprintf(frame, sizeof(frame),
            "id=%s cycle=%s kind=row ordinal=%u base=%016llx size=%016llx source=%u hotplug=%u",
            N10_SHA256_KAT_ID, (const char *)n10_cycle, row->ordinal,
            (unsigned long long)row->base, (unsigned long long)row->size,
            row->flags & 3U, !!(row->flags & 4U));
        pr_info("N10MEMARGS1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    }
    count = scnprintf(frame, sizeof(frame),
        "id=%s cycle=%s kind=end seen=%u stored=%u dropped=%u flags=%08x ended=%u offset=%d depth=%d rc=%d complete=%u raw_binding=0 add_success=0 reservations=0 ownership=0",
        N10_SHA256_KAT_ID, (const char *)n10_cycle, n10_memory.seen, n10_memory.stored,
        n10_memory.dropped, flags, n10_memory.ended, n10_memory.offset,
        n10_memory.depth, n10_memory.rc, complete);
    pr_info("N10MEMARGS1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    return 0; /* Diagnostic outcome never changes Linux admission/recovery. */
}
