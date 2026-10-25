/* SPDX-License-Identifier: GPL-2.0-only */
/* Included only in the opt-in RAM-access diagnostic, inside init.c.
 * Uses this boot's reservation. Never imports a previous boot's address.
 * No MMIO, executable branch, CPU shutdown, partition or persistent writes.
 */
#include <linux/sched.h>
#include <asm/memory.h>
#define N10_ACCESS_FENCE() smp_mb()
#define N10_ACCESS_RESCHED() cond_resched()
#include "note10_window_access_core.h"

static void __init note10_test_xnu_window_access(unsigned long reserved,
                                                unsigned long pages,
                                                unsigned long invalid)
{
    struct n10_access_result result = {0};
    const u64 words = N10_WINDOW_SIZE / sizeof(u64);
    u64 *memory;
    unsigned int sequence;
    char frame[512];

    result.status = 3;
    if (n10_window_status != 1 || invalid || reserved != pages ||
        pages != (N10_WINDOW_SIZE >> PAGE_SHIFT) ||
        !n10_window_base || (n10_window_base & (N10_WINDOW_ALIGN - 1)) ||
        n10_window_base > N10_WINDOW_LIMIT - N10_WINDOW_SIZE)
        goto report;
    memory = phys_to_virt(n10_window_base);
    result.status = 4;
    if (!virt_addr_valid(memory) || !virt_addr_valid(memory + words - 1) ||
        virt_to_phys(memory) != n10_window_base ||
        virt_to_phys(memory + words - 1) != n10_window_base + N10_WINDOW_SIZE - 8)
        goto report;
    n10_access_test(memory, words, &result);
report:
    for (sequence = 0; sequence < 32; ++sequence) {
        int length = scnprintf(frame, sizeof(frame),
            "id=%s seq=%u base=%llx size=%llx words=%llu written=%llu checked=%llu zeroed=%llu zero_checked=%llu mismatches=%llu rounds=%u status=%u",
            N10_RESERVE_BUILD_ID, sequence,
            (unsigned long long)n10_window_base, N10_WINDOW_SIZE,
            (unsigned long long)words, (unsigned long long)result.written,
            (unsigned long long)result.checked, (unsigned long long)result.zeroed,
            (unsigned long long)result.zero_checked, (unsigned long long)result.mismatches,
            result.rounds, result.status);
        pr_info("N10MEM1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, length));
    }
}
