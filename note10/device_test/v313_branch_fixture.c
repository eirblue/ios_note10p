/* SPDX-License-Identifier: GPL-2.0-only */
/* v313 host fixture (new cases only): the N313PS20 record tag, a C mirror of the new stub Block A (entry word is an
 * unconditional B, TGran16 1 or 2, window end < 2^39, x18 = B + kernel offset + entry_offset), a C mirror of the Block B
 * dc civac line range, and the N313PS2T record validator. Synthetic values only: v312 synthetic entry 0x4010 / word
 * 0x14000001, synthetic window bases, MMFR0 and CTR values; no real kernel bytes, entry, address or register value. */
#include <stdio.h>
#include "v313_abi_contract.h"
#include "v313_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 32 MiB-aligned window base >= 2 GiB (record vectors) */
#define BRANCH_BASE 0x880000000ULL   /* synthetic window base for the x18 vector */
#define MPIDR 0x81000010ULL          /* synthetic raw MPIDR: affinity 0x10 */
#define ADT_NODES 13U
#define ADT_FNV 0xc1cb3618U          /* synthetic record field */
#define ARGS_FNV 0xaee810a3U         /* synthetic record field */
#define IMAGE_FNV 0x4e154d31U        /* v312 synthetic image word-FNV (record field) */
#define IMAGE_TICKS 0x1234U          /* synthetic MMU-off hash ticks */
#define ENTRY 0x4010U                /* v312 synthetic entry offset */
#define ENTRY_WORD 0x14000001U       /* v312 synthetic 'b .+4' at the entry */
#define EXPECTED_CHECKS 21
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

_Static_assert(N313_B_OPCODE_MASK == 0xfc000000 && N313_B_OPCODE == 0x14000000, "unconditional B encoding");
_Static_assert(N313_MMFR0_TGRAN16_SHIFT == 20 && N313_PA_LIMIT_SHIFT == 39, "TGran16 field and PA limit");
_Static_assert(N311_WINDOW_ALIGN % 0x2000000 == 0 && N311_VIRT_BASE % 0x2000000 == 0, "32 MiB L2 blocks");
_Static_assert(N304_RECORD_BYTES == 250 && N304_RECORD_BYTES == N304_HOST_RECORD_BYTES, "record bytes");

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v313 fixture failed at line %d\n", __LINE__); \
            return 1;                                                     \
        }                                                                 \
        ++checks;                                                         \
    } while (0)

/* Mirror of v313 Block A: and/movz/cmp (B opcode), add x18, ubfx/sub/cmp/b.hi (TGran16), mov/add/sub/lsr/cbnz (PA). */
static int block_a(uint32_t word, uint64_t mmfr0, uint64_t base, uint32_t entry, uint64_t *x18)
{
    if ((word & N313_B_OPCODE_MASK) != N313_B_OPCODE)
        return 0;
    *x18 = base + N311_KERNEL_OFFSET + entry;
    if ((uint32_t)((mmfr0 >> N313_MMFR0_TGRAN16_SHIFT) & 15) - 1U > 1U)
        return 0;
    return ((base + N311_WINDOW_BYTES - 1) >> N313_PA_LIMIT_SHIFT) == 0;
}

/* Mirror of v313 Block B: DminLine = 4 << CTR_EL0[19:16]; lines from record & ~(line - 1) while < record + 250. */
static void block_b(uint64_t ctr, uint64_t record, uint64_t *first, uint32_t *lines)
{
    uint64_t line = 4ULL << ((ctr >> 16) & 15), at = record & ~(line - 1);

    *first = at;
    for (*lines = 0; at < record + N304_RECORD_BYTES; at += line)
        ++*lines;
}

static void put_hex(char *field, size_t digits, uint64_t value)
{
    static const char hex[] = "0123456789abcdef";

    while (digits) {
        field[--digits] = hex[value & 15];
        value >>= 4;
    }
}

static void make_record(char *record, const char *tag, uint64_t r3)
{
    char text[N304_HOST_RECORD_BYTES + 1];

    snprintf(text, sizeof(text), N304_HOST_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID);
    memcpy(record, text, N304_HOST_RECORD_BYTES);
    memcpy(record, tag, 7);
    put_hex(record + N304_HOST_REG_OFFSET, 16, BASE);
    put_hex(record + N304_HOST_REG_OFFSET + N304_HOST_REG_STRIDE, 16, MPIDR);
    put_hex(record + N304_HOST_REG_OFFSET + 2 * N304_HOST_REG_STRIDE, 16, (uint64_t)IMAGE_TICKS << 32 | IMAGE_FNV);
    put_hex(record + N304_HOST_REG_OFFSET + 3 * N304_HOST_REG_STRIDE, 16, r3);
    put_hex(record + N304_HOST_ARGS_HASH_OFFSET, 8, ARGS_FNV);
    put_hex(record + N304_HOST_ADT_HASH_OFFSET, 8, ADT_FNV);
    put_hex(record + N304_HOST_ADT_LENGTH_OFFSET, 2, ADT_NODES);
    put_hex(record + N304_HOST_SCTLR_OFFSET, 16, 0x30d00800);
    record[N304_HOST_EL_OFFSET] = '1';
    record[N304_HOST_DAIF_OFFSET] = 'f';
    record[N304_HOST_COMMIT_OFFSET] = N304_HOST_COMMITTED;
    put_hex(record + N304_HOST_CSUM_OFFSET, 8, n306_host_body_checksum(record));
}

int main(void)
{
    char text[N304_RECORD_BYTES + 1], record[N304_HOST_RECORD_BYTES], altered[N304_HOST_RECORD_BYTES];
    const uint64_t tgran1 = 1ULL << N313_MMFR0_TGRAN16_SHIFT;
    const uint64_t limit = 1ULL << N313_PA_LIMIT_SHIFT;
    const uint32_t accept_words[] = {ENTRY_WORD, 0x17ffffffU};
    const uint32_t reject_words[] = {0x94000001U /* bl */, 0xd503201fU /* nop */, 0x54000000U /* b.cond */};
    const uint64_t reject_tgran[] = {0, 3, 15};
    const struct {
        uint64_t ctr, record, first;
        uint32_t lines;
    } ranges[] = {
        {4ULL << 16, 0x100000ULL, 0x100000ULL, 4},          /* 64 B lines, line-aligned record */
        {4ULL << 16, 0x100030ULL, 0x100000ULL, 5},          /* 64 B lines, unaligned record */
        {3ULL << 16, 0x100000ULL, 0x100000ULL, 8},          /* 32 B lines, line-aligned record */
        {3ULL << 16, 0x100010ULL, 0x100000ULL, 9},          /* 32 B lines, unaligned record */
    };
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10, .args_hash = ARGS_FNV,
                                                 .adt_hash = ADT_FNV, .adt_nodes = ADT_NODES, .image_hash = IMAGE_FNV,
                                                 .entry_offset = ENTRY, .entry_word = ENTRY_WORD};
    uint64_t x18, first;
    uint32_t lines;

    /* Kernel record format: 250 bytes with tag N313PS20. */
    CHECK(snprintf(text, sizeof(text), N304_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_RECORD_BYTES &&
          !memcmp(text, "N313PS20", 8));

    /* Block A: entry word, TGran16, PA limit, x18. */
    for (size_t i = 0; i < sizeof(accept_words) / sizeof(accept_words[0]); ++i)
        CHECK(block_a(accept_words[i], tgran1, BRANCH_BASE, ENTRY, &x18));
    for (size_t i = 0; i < sizeof(reject_words) / sizeof(reject_words[0]); ++i)
        CHECK(!block_a(reject_words[i], tgran1, BRANCH_BASE, ENTRY, &x18));
    CHECK(block_a(ENTRY_WORD, tgran1, BRANCH_BASE, ENTRY, &x18));
    CHECK(block_a(ENTRY_WORD, 2 * tgran1, BRANCH_BASE, ENTRY, &x18));
    for (size_t i = 0; i < sizeof(reject_tgran) / sizeof(reject_tgran[0]); ++i)
        CHECK(!block_a(ENTRY_WORD, reject_tgran[i] << N313_MMFR0_TGRAN16_SHIFT | 0xff0ff, BRANCH_BASE, ENTRY, &x18));
    CHECK(block_a(ENTRY_WORD, tgran1, limit - N311_WINDOW_BYTES, ENTRY, &x18));
    CHECK(!block_a(ENTRY_WORD, tgran1, limit + N311_WINDOW_ALIGN - N311_WINDOW_BYTES, ENTRY, &x18));
    CHECK(block_a(ENTRY_WORD, tgran1, BRANCH_BASE, ENTRY, &x18) && x18 == BRANCH_BASE + 0x1004000ULL + 0x4010ULL);

    /* Block B: exact first line and line count. */
    for (size_t i = 0; i < sizeof(ranges) / sizeof(ranges[0]); ++i) {
        block_b(ranges[i].ctr | 0x80000004ULL, ranges[i].record, &first, &lines);
        CHECK(first == ranges[i].first && lines == ranges[i].lines);
    }

    /* N313PS2T record validator. */
    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    make_record(record, "N313PS2", (uint64_t)ENTRY << 32 | ENTRY_WORD);
    CHECK(n306_host_record_valid(record, sizeof(record), &expected));
    make_record(altered, "N312PS2", (uint64_t)ENTRY << 32 | ENTRY_WORD);         /* v312 record */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, "N313PS2", (uint64_t)ENTRY << 32 | (ENTRY_WORD ^ 1));   /* wrong r[3] */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    if (checks != EXPECTED_CHECKS) {
        fprintf(stderr, "v313 fixture check count %d\n", checks);
        return 1;
    }
    puts("v313 branch fixture PASS");
    return 0;
}
