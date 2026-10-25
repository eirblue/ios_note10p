/* SPDX-License-Identifier: GPL-2.0-only */
/* Caller supplies u64/u32, READ_ONCE/WRITE_ONCE, barrier and reschedule.
 * Operates only on a buffer already exclusively reserved by the caller.
 * Cached Linux memory access test; not cache-off or DMA handoff validation.
 */
#ifndef NOTE10_WINDOW_ACCESS_CORE_H
#define NOTE10_WINDOW_ACCESS_CORE_H
struct n10_access_result {
    u64 written, checked, zeroed, zero_checked, mismatches;
    u32 rounds, status;
};

static u64 n10_access_pattern(u64 index, unsigned int round)
{
    u64 value = 0xa5c39e72d6410bf8ULL ^
                (index * 0x9e3779b97f4a7c15ULL);
    return round ? ~value : value;
}

static void n10_access_test(u64 *memory, u64 words,
                            struct n10_access_result *result)
{
    u64 i;
    unsigned int round;
    struct n10_access_result r = {0};

    if (!memory || !words || words > (256ULL << 20) / 8) {
        r.status = 1;
        *result = r;
        return;
    }
    for (round = 0; round < 2; ++round) {
        for (i = 0; i < words; ++i) {
            WRITE_ONCE(memory[i], n10_access_pattern(i, round));
            ++r.written;
            if ((i & 65535) == 65535) N10_ACCESS_RESCHED();
        }
        N10_ACCESS_FENCE();
        for (i = 0; i < words; ++i) {
            if (READ_ONCE(memory[i]) != n10_access_pattern(i, round))
                ++r.mismatches;
            ++r.checked;
            if ((i & 65535) == 65535) N10_ACCESS_RESCHED();
        }
        ++r.rounds;
        if (r.mismatches) break;
    }
    for (i = 0; i < words; ++i) {
        WRITE_ONCE(memory[i], 0);
        ++r.zeroed;
        if ((i & 65535) == 65535) N10_ACCESS_RESCHED();
    }
    N10_ACCESS_FENCE();
    for (i = 0; i < words; ++i) {
        if (READ_ONCE(memory[i]) != 0) ++r.mismatches;
        ++r.zero_checked;
        if ((i & 65535) == 65535) N10_ACCESS_RESCHED();
    }
    r.status = r.mismatches ? 2 : 0;
    *result = r;
}
#endif
