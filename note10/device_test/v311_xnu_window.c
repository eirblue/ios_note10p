/* SPDX-License-Identifier: GPL-2.0-only */
/* v311: installed as arch/arm64/mm/n311_xnu_window.c and included by arm64/mm/init.c before arm64_memblock_init.
 * Same find/reserve call as the device-proven v4 xnu_reserve.c; no write to the window, no initcall, no frames. */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/memblock.h>
#include "../kernel/n304_abi_contract.h"

phys_addr_t n311_window_base;
int n311_window_status;

/* Called once at the end of arm64_memblock_init, after every kernel/initrd/DT/crashkernel/CMA reservation,
 * so a successful find lies in free, mapped DRAM (memblock skips reserved and no-map ranges). */
static void __init n311_reserve_window(void)
{
    phys_addr_t base = memblock_find_in_range(N311_WINDOW_MIN, 1ULL << 40, N311_WINDOW_BYTES, N311_WINDOW_ALIGN);

    if (!base || base % N311_WINDOW_ALIGN || base > (1ULL << 40) - N311_WINDOW_BYTES ||
        !memblock_is_region_memory(base, N311_WINDOW_BYTES) ||
        memblock_is_region_reserved(base, N311_WINDOW_BYTES)) {
        base = 0;
        n311_window_status = -1;
    } else if (memblock_reserve(base, N311_WINDOW_BYTES)) {
        base = 0;
        n311_window_status = -2;
    } else {
        n311_window_base = base;
        n311_window_status = 1;
    }
    pr_info("N311WIN base=%016llx size=%016llx align=%016llx status=%d\n", (unsigned long long)base,
            (unsigned long long)N311_WINDOW_BYTES, (unsigned long long)N311_WINDOW_ALIGN, n311_window_status);
}
