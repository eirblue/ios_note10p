/* SPDX-License-Identifier: GPL-2.0-only */
/* v314 host fixture (new cases only): the N314PS20 record tag and N314 span constants, a C mirror of the two new Linux
 * n304_enter conditions (record span 266 must fit before log end - 8 and stay disjoint from the window and the cursor),
 * a C mirror of the Block B dc civac line range over [x3, x3 + 266), and the N314PS2T validator with the
 * n314_crumb_level breadcrumb parser. Synthetic values only: synthetic log/record/cursor/window positions, the v312
 * synthetic entry 0x4010 / word 0x14000001, synthetic CTR values; no real kernel bytes, entry, address or register. */
#include <stdio.h>
#include "v314_abi_contract.h"
#include "v314_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 32 MiB-aligned window base >= 2 GiB (record vectors) */
#define LOG_BASE 0x10000000ULL       /* synthetic dss log base below the window */
#define LOG_BYTES 0x200000ULL        /* synthetic dss log size */
#define MPIDR 0x81000010ULL          /* synthetic raw MPIDR: affinity 0x10 */
#define ADT_NODES 13U
#define ADT_FNV 0xc1cb3618U          /* synthetic record field */
#define ARGS_FNV 0xaee810a3U         /* synthetic record field */
#define IMAGE_FNV 0x4e154d31U        /* v312 synthetic image word-FNV (record field) */
#define IMAGE_TICKS 0x1234U          /* synthetic MMU-off hash ticks */
#define ENTRY 0x4010U                /* v312 synthetic entry offset */
#define ENTRY_WORD 0x14000001U       /* v312 synthetic 'b .+4' at the entry */
#define EXPECTED_CHECKS 19
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

_Static_assert(N314_CRUMB_BYTES == 16 && N314_RECORD_SPAN == 266, "record + two 8-byte breadcrumbs");
_Static_assert(N314_RECORD_SPAN == N304_RECORD_BYTES + 2 * N314_HOST_CRUMB_BYTES, "host crumb bytes");
_Static_assert(N304_META_OFFSET + N304_CURSOR == 1424 && N304_META_OFFSET + N304_NEXT == 1432, "meta cursor/next");
_Static_assert(N304_RECORD_BYTES == 250 && N304_RECORD_BYTES == N304_HOST_RECORD_BYTES, "record bytes");

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v314 fixture failed at line %d\n", __LINE__); \
            return 1;                                                     \
        }                                                                 \
        ++checks;                                                         \
    } while (0)

/* Mirror of the v314 n304_enter refusal: tail = log end - 8 - record (n303_claim_ok), tail >= 266, record span vs window,
 * cursor vs window, record span vs cursor, cursor 4-aligned. */
static int enter_ok(uint64_t record, uint64_t cursor, uint64_t window)
{
    uint64_t tail = LOG_BASE + LOG_BYTES - 8 - record;

    return tail >= N314_RECORD_SPAN && n304_disjoint(record, N314_RECORD_SPAN, window, N311_WINDOW_BYTES) &&
           n304_disjoint(cursor, sizeof(uint32_t), window, N311_WINDOW_BYTES) &&
           n304_disjoint(record, N314_RECORD_SPAN, cursor, sizeof(uint32_t)) && !(cursor & 3);
}

/* Mirror of v314 Block B: DminLine = 4 << CTR_EL0[19:16]; lines from record & ~(line - 1) while < record + 266. */
static void block_b(uint64_t ctr, uint64_t record, uint64_t *first, uint32_t *lines)
{
    uint64_t line = 4ULL << ((ctr >> 16) & 15), at = record & ~(line - 1);

    *first = at;
    for (*lines = 0; at < record + N314_RECORD_SPAN; at += line)
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

/* Crumb level of the bytes after a committed record: record (250) followed by tail. */
static int level_after(const char *record, const char *tail, size_t len)
{
    char buffer[N304_HOST_RECORD_BYTES + 32];

    memcpy(buffer, record, N304_HOST_RECORD_BYTES);
    memcpy(buffer + N304_HOST_RECORD_BYTES, tail, len);
    return n314_crumb_level(buffer + N304_HOST_RECORD_BYTES, len);
}

int main(void)
{
    char text[N304_RECORD_BYTES + 1], record[N304_HOST_RECORD_BYTES], altered[N304_HOST_RECORD_BYTES];
    const uint64_t record_at = LOG_BASE + LOG_BYTES - 8 - N314_RECORD_SPAN; /* tail exactly 266 */
    const uint64_t far_cursor = LOG_BASE + LOG_BYTES + 0x1000;              /* header word outside the log */
    const struct {
        uint64_t ctr, record, first;
        uint32_t lines;
    } ranges[] = {
        {4ULL << 16, 0x100000ULL, 0x100000ULL, 5},          /* 64 B lines, line-aligned record */
        {4ULL << 16, 0x100030ULL, 0x100000ULL, 5},          /* 64 B lines, unaligned record */
        {3ULL << 16, 0x100000ULL, 0x100000ULL, 9},          /* 32 B lines, line-aligned record */
        {3ULL << 16, 0x100010ULL, 0x100000ULL, 9},          /* 32 B lines, unaligned record */
    };
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10, .args_hash = ARGS_FNV,
                                                 .adt_hash = ADT_FNV, .adt_nodes = ADT_NODES, .image_hash = IMAGE_FNV,
                                                 .entry_offset = ENTRY, .entry_word = ENTRY_WORD};
    uint64_t first;
    uint32_t lines;

    /* Kernel record format: 250 bytes with tag N314PS20. */
    CHECK(snprintf(text, sizeof(text), N304_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_RECORD_BYTES &&
          !memcmp(text, "N314PS20", 8));

    /* Linux n304_enter: tail and span disjointness. */
    CHECK(enter_ok(record_at, far_cursor, BASE));                                  /* tail 266 */
    CHECK(!enter_ok(record_at + 1, far_cursor, BASE));                             /* tail 265 */
    CHECK(!enter_ok(0x10001000ULL, 0x10001000ULL + N304_RECORD_BYTES + 4, BASE));  /* cursor inside the crumb span */
    CHECK(enter_ok(0x10001000ULL, 0x10001000ULL + N314_RECORD_SPAN + 2, BASE));    /* cursor right after the span */
    CHECK(!enter_ok(0x10001000ULL, 0x10000ff0ULL, 0x10001000ULL + 260));             /* window inside the crumb span */
    CHECK(enter_ok(0x10001000ULL, 0x10000ff0ULL, 0x10001000ULL + N314_RECORD_SPAN)); /* window right after the span */

    /* Block B: exact first line and line count over the 266-byte span. */
    for (size_t i = 0; i < sizeof(ranges) / sizeof(ranges[0]); ++i) {
        block_b(ranges[i].ctr | 0x80000004ULL, ranges[i].record, &first, &lines);
        CHECK(first == ranges[i].first && lines == ranges[i].lines);
    }

    /* N314PS2T validator and breadcrumb levels. */
    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    make_record(record, "N314PS2", (uint64_t)ENTRY << 32 | ENTRY_WORD);
    CHECK(n306_host_record_valid(record, sizeof(record), &expected));
    make_record(altered, "N313PS2", (uint64_t)ENTRY << 32 | ENTRY_WORD);         /* v313 record */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, "N314PS2", (uint64_t)ENTRY << 32 | (ENTRY_WORD ^ 1));   /* wrong r[3] */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    CHECK(level_after(record, "N314X1E\nN314X2M\n[0:", 19) == 2);
    CHECK(level_after(record, "N314X1E\n[0:", 11) == 1);
    CHECK(level_after(record, "[0:", 3) == 0);
    CHECK(level_after(record, "N314X2M\n[0:", 11) == 0);
    CHECK(level_after(record, "N314X1", 6) == 0);
    if (checks != EXPECTED_CHECKS) {
        fprintf(stderr, "v314 fixture check count %d\n", checks);
        return 1;
    }
    puts("v314 crumb fixture PASS");
    return 0;
}
