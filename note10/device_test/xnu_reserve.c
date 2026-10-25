/* SPDX-License-Identifier: GPL-2.0-only */
/* Included by pinned arm64/mm/init.c before arm64_memblock_init.
 * Reservation diagnostic only: does not write the window or execute XNU.
 */
#include <linux/init.h>
#include <linux/memblock.h>
#include <linux/mm.h>

#define N10_WINDOW_SIZE (256ULL << 20)
#define N10_WINDOW_ALIGN (32ULL << 20)
#define N10_WINDOW_LIMIT (1ULL << 40)

static phys_addr_t n10_window_base;
static int n10_window_status;

static void __init note10_reserve_xnu_window(void)
{
    phys_addr_t base;

    base = memblock_find_in_range(1ULL << 31, N10_WINDOW_LIMIT,
                                  N10_WINDOW_SIZE, N10_WINDOW_ALIGN);
    if (!base || (base & (N10_WINDOW_ALIGN - 1)) ||
        base > N10_WINDOW_LIMIT - N10_WINDOW_SIZE ||
        !memblock_is_region_memory(base, N10_WINDOW_SIZE) ||
        memblock_is_region_reserved(base, N10_WINDOW_SIZE)) {
        n10_window_status = -1;
        pr_err("N10RAM1 FAILED stage=find\n");
        return;
    }
    if (memblock_reserve(base, N10_WINDOW_SIZE)) {
        n10_window_status = -2;
        pr_err("N10RAM1 FAILED stage=reserve\n");
        return;
    }
    n10_window_base = base;
    n10_window_status = 1;
    pr_info("N10RAM1 RESERVED base=%llx size=%llx align=%llx\n",
            (unsigned long long)base, N10_WINDOW_SIZE, N10_WINDOW_ALIGN);
}

static int __init note10_check_xnu_window(void)
{
    unsigned long start, count, i, reserved = 0, invalid = 0;

    if (n10_window_status != 1) {
        pr_err("N10RAM1 FAILED stage=late-no-window\n");
        return 0;
    }
    start = PHYS_PFN(n10_window_base);
    count = N10_WINDOW_SIZE >> PAGE_SHIFT;
    for (i = 0; i < count; ++i) {
        if (!pfn_valid(start + i)) {
            ++invalid;
            continue;
        }
        if (PageReserved(pfn_to_page(start + i)))
            ++reserved;
    }
    pr_info("N10RAM1 CHECK pages=%lu reserved=%lu invalid=%lu shift=%u\n",
            count, reserved, invalid, (unsigned int)PAGE_SHIFT);
    if (reserved != count || invalid)
        pr_err("N10RAM1 FAILED stage=page-state\n");
    /* Reserved pages remain excluded from Linux's allocator until reboot.
     * This does not prove DMA quiescence or global SoC ownership.
     */
    return 0;
}
late_initcall(note10_check_xnu_window);
