/* SPDX-License-Identifier: BSD-2-Clause */
/* EXYNOS declared managed-range checks; no ownership or boot-budget claim. */
#if !defined(ARM64_BOARD_CONFIG_EXYNOS9825) || !defined(__ARM_16K_PG__) || CONFIG_SPTM || XNU_MONITOR || __ARM_KERNEL_PROTECT__ || KASAN
#error unsupported Exynos checked page allocation configuration
#endif
#if defined(KERNEL_INTEGRITY_KTRR) || defined(KERNEL_INTEGRITY_CTRR) || defined(KERNEL_INTEGRITY_PV_CTRR)
#error unsupported Exynos static page protection policy
#endif
_Static_assert(ARM_PGBYTES == 16384, "Exynos hardware page must be 16KiB");

static int
n10_pt_boot_input_ok(uint64_t base, uint64_t raw_bytes, uint64_t max_memory, uint64_t page)
{
    uint64_t end, managed;
    if (page != 16384 || (base & (page - 1)) || !raw_bytes ||
        raw_bytes > ~(uint64_t)0 - base) {
        return 0;
    }
    end = (base + raw_bytes) & ~(page - 1);
    if (end <= base) {
        return 0;
    }
    managed = end - base;
    if (max_memory && max_memory < managed && (max_memory & (page - 1))) {
        return 0;
    }
    return 1;
}

static int
n10_pt_next(uint64_t base, uint64_t managed, uint64_t floor,
    uint64_t cursor, uint64_t page, uint64_t *next)
{
    uint64_t end;
    if (page != 16384 || !next || !managed ||
        ((base | managed | floor | cursor) & (page - 1)) ||
        managed > ~(uint64_t)0 - base) {
        return 0;
    }
    end = base + managed;
    if (floor < base || floor > cursor || cursor > end || end - cursor < page) {
        return 0;
    }
    *next = cursor + page;
    return 1;
}

static void
n10_pt_require_boot_input(uint64_t base, uint64_t raw_bytes, uint64_t max_memory)
{
    if (!n10_pt_boot_input_ok(base, raw_bytes, max_memory, PAGE_SIZE)) {
        panic("Exynos page allocator boot input refused");
    }
}

static vm_offset_t
n10_exynos_dynamic_ptpage(void)
{
    uint64_t next;
    const uint64_t cursor = avail_start;
    vm_offset_t vaddr;
    if (!n10_pt_next(gPhysBase, mem_size, first_avail_phys, cursor, PAGE_SIZE, &next)) {
        panic("Exynos page allocator range exhausted or invalid");
    }
    /* Preserve native conversion-before-bump: conversion may itself refuse. */
    vaddr = phystokv(cursor);
    avail_start = next;
    return vaddr;
}
