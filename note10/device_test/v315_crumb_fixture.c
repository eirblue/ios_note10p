/* SPDX-License-Identifier: GPL-2.0-only */
/* v315 host fixture (new cases only): the N315PS20 record tag and N315 span/memSize constants, a C mirror of the Linux
 * n304_enter span conditions over the 274-byte record + three-crumb span, a C mirror of the Block B dc civac line range
 * over [x3, x3 + 274), the N315PS2T validator with the order-independent n315_crumb_trace parser, the v315 boot_args
 * (memSize N315_BOOT_MEMSIZE, memSizeActual the window), a C mirror of XNU's bootstrap builder size rule and a C mirror of
 * the stub's v315 boot_args checks. Synthetic values only: synthetic log/record/cursor/window positions, the v312 synthetic
 * entry 0x4010 / word 0x14000001, synthetic CTR values; no real kernel bytes, entry, address or register. */
#include <stdio.h>
#include "v315_abi_contract.h"
#include "v315_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 32 MiB-aligned window base >= 2 GiB */
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
#define IMAGE_BYTES 0x1240000U       /* synthetic loaded-image size (16 KiB multiple) */
#define BUILDER_MAX 0x2000000ULL     /* XNU Exynos bootstrap builder: at most 32 MiB from the image PA */
#define EXPECTED_CHECKS 32
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

_Static_assert(N315_CRUMB_BYTES == 24 && N315_RECORD_SPAN == 274, "record + three 8-byte checkpoint crumbs");
_Static_assert(N315_RECORD_SPAN == N304_RECORD_BYTES + 3 * N315_HOST_CRUMB_BYTES, "host crumb bytes");
_Static_assert(N315_CRUMB_BYTES - 8 == 16, "guard window next .. next + 16");
_Static_assert(N304_META_OFFSET + N304_CURSOR == 1424 && N304_META_OFFSET + N304_NEXT == 1432, "meta cursor/next");
_Static_assert(N304_RECORD_BYTES == 250 && N304_RECORD_BYTES == N304_HOST_RECORD_BYTES, "record bytes");
_Static_assert(N315_BOOT_MEMSIZE == 0x3004000 && N311_KERNEL_OFFSET == 0x1004000, "boot memSize = kernel offset + 32 MiB");

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v315 fixture failed at line %d\n", __LINE__); \
            return 1;                                                     \
        }                                                                 \
        ++checks;                                                         \
    } while (0)

/* Mirror of the v315 n304_enter refusal: tail = log end - 8 - record (n303_claim_ok), tail >= 274, record span vs window,
 * cursor vs window, record span vs cursor, cursor 4-aligned. */
static int enter_ok(uint64_t record, uint64_t cursor, uint64_t window)
{
    uint64_t tail = LOG_BASE + LOG_BYTES - 8 - record;

    return tail >= N315_RECORD_SPAN && n304_disjoint(record, N315_RECORD_SPAN, window, N311_WINDOW_BYTES) &&
           n304_disjoint(cursor, sizeof(uint32_t), window, N311_WINDOW_BYTES) &&
           n304_disjoint(record, N315_RECORD_SPAN, cursor, sizeof(uint32_t)) && !(cursor & 3);
}

/* Mirror of v315 Block B: DminLine = 4 << CTR_EL0[19:16]; lines from record & ~(line - 1) while < record + 274. */
static void block_b(uint64_t ctr, uint64_t record, uint64_t *first, uint32_t *lines)
{
    uint64_t line = 4ULL << ((ctr >> 16) & 15), at = record & ~(line - 1);

    *first = at;
    for (*lines = 0; at < record + N315_RECORD_SPAN; at += line)
        ++*lines;
}

/* Mirror of the bootstrap builder size rule on x2 = memSize - (image PA - physBase): nonzero, 16 KiB aligned, <= 32 MiB. */
static int builder_size_ok(uint64_t memsize)
{
    uint64_t size = memsize - N311_KERNEL_OFFSET;

    return memsize > N311_KERNEL_OFFSET && !(size % 0x4000) && size <= BUILDER_MAX;
}

/* Mirror of the v315 stub boot_args checks: kernel offset + image_bytes <= N315_BOOT_MEMSIZE, memSize == N315_BOOT_MEMSIZE,
 * topOfKernelData == B + kernel offset + image_bytes, memSizeActual >= window. 1 = accepted, 0 = park. */
static int stub_args_ok(const uint8_t *args, uint64_t base, uint64_t image_bytes)
{
    uint64_t end = N311_KERNEL_OFFSET + image_bytes;

    return end <= N315_BOOT_MEMSIZE && n312_le64(args + N305_MEMSIZE) == N315_BOOT_MEMSIZE &&
           n312_le64(args + N305_TOP) == base + end && n312_le64(args + N305_MEMACTUAL) >= N311_WINDOW_BYTES;
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

/* Crumb trace of the bytes after a committed record: mask == want_mask and builder code == want_code. */
static int trace_is(const char *record, const char *tail, size_t len, int want_mask, int want_code)
{
    char buffer[N304_HOST_RECORD_BYTES + 40];
    int code = -2, mask;

    memcpy(buffer, record, N304_HOST_RECORD_BYTES);
    memcpy(buffer + N304_HOST_RECORD_BYTES, tail, len);
    mask = n315_crumb_trace(buffer + N304_HOST_RECORD_BYTES, len, &code);
    return mask == want_mask && code == want_code;
}

int main(void)
{
    char text[N304_RECORD_BYTES + 1], record[N304_HOST_RECORD_BYTES], altered[N304_HOST_RECORD_BYTES];
    uint8_t args[N304_ARGS_BYTES], mutated[N304_ARGS_BYTES];
    const uint64_t record_at = LOG_BASE + LOG_BYTES - 8 - N315_RECORD_SPAN; /* tail exactly 274 */
    const uint64_t far_cursor = LOG_BASE + LOG_BYTES + 0x1000;              /* header word outside the log */
    const struct {
        uint64_t ctr, record, first;
        uint32_t lines;
    } ranges[] = {
        {4ULL << 16, 0x100000ULL, 0x100000ULL, 5},          /* 64 B lines, line-aligned record */
        {4ULL << 16, 0x100030ULL, 0x100000ULL, 6},          /* 64 B lines, unaligned record */
        {3ULL << 16, 0x100000ULL, 0x100000ULL, 9},          /* 32 B lines, line-aligned record */
        {3ULL << 16, 0x100010ULL, 0x100000ULL, 10},         /* 32 B lines, unaligned record */
    };
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10, .args_hash = ARGS_FNV,
                                                 .adt_hash = ADT_FNV, .adt_nodes = ADT_NODES, .image_hash = IMAGE_FNV,
                                                 .entry_offset = ENTRY, .entry_word = ENTRY_WORD};
    uint64_t first;
    uint32_t lines;

    /* Kernel record format: 250 bytes with tag N315PS20. */
    CHECK(snprintf(text, sizeof(text), N304_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_RECORD_BYTES &&
          !memcmp(text, "N315PS20", 8));

    /* Linux n304_enter: tail and span disjointness over 274 bytes. */
    CHECK(enter_ok(record_at, far_cursor, BASE));                                  /* tail 274 */
    CHECK(!enter_ok(record_at + 1, far_cursor, BASE));                             /* tail 273 */
    CHECK(!enter_ok(0x10001000ULL, 0x10001000ULL + 268, BASE));                    /* cursor right after record + 266 */
    CHECK(enter_ok(0x10001000ULL, 0x10001000ULL + N315_RECORD_SPAN + 2, BASE));    /* cursor after record + 274 */

    /* Block B: exact first line and line count over the 274-byte span. */
    for (size_t i = 0; i < sizeof(ranges) / sizeof(ranges[0]); ++i) {
        block_b(ranges[i].ctr | 0x80000004ULL, ranges[i].record, &first, &lines);
        CHECK(first == ranges[i].first && lines == ranges[i].lines);
    }

    /* N315PS2T validator and the order-independent checkpoint trace. */
    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    make_record(record, "N315PS2", (uint64_t)ENTRY << 32 | ENTRY_WORD);
    CHECK(n306_host_record_valid(record, sizeof(record), &expected));
    make_record(altered, "N314PS2", (uint64_t)ENTRY << 32 | ENTRY_WORD);         /* v314 record */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    CHECK(trace_is(record, "N315E1-\nN315B21\n[0:", 19, 3, 1));
    CHECK(trace_is(record, "N315E1-\nN315B20\nN315M3-\n[0:", 27, 7, 0));
    CHECK(trace_is(record, "N315B21\n[0:", 11, 2, 1));
    CHECK(trace_is(record, "N315E1-\n[0:", 11, 1, -1));
    CHECK(trace_is(record, "[0:", 3, 0, -1));
    CHECK(trace_is(record, "N315E1-\nN315E1-\nN315M3-\n", 24, 1, -1));        /* duplicate stops the trace */
    CHECK(trace_is(record, "N315E1-\nN315B2g\nN315M3-\n", 24, 1, -1));        /* invalid value char stops */
    CHECK(trace_is(record, "N315B2", 6, 0, -1));                                /* truncated */
    CHECK(trace_is(record, "N314X1E\n", 8, 0, -1));                             /* v314 crumb */
    CHECK(trace_is(record, "N315M3-\nN315B20\n", 16, 6, 0));                    /* order independent */

    /* boot_args: memSize N315_BOOT_MEMSIZE at +24, memSizeActual the window at +1144, topOfKernel; image bound 32 MiB. */
    CHECK(n311_arguments(BASE, 2048, IMAGE_BYTES, args) == N10_RT_OK);
    CHECK(n312_le64(args + N305_MEMSIZE) == 0x3004000ULL && n312_le64(args + N305_MEMACTUAL) == 0x10000000ULL &&
          n312_le64(args + N305_TOP) == BASE + 0x1004000ULL + IMAGE_BYTES && n312_le64(args + N305_PHYS) == BASE);
    CHECK(n311_image_bytes_ok(0x2000000) && n311_arguments(BASE, 2048, 0x2000000, mutated) == N10_RT_OK);
    CHECK(!n311_image_bytes_ok(0x2004000) && n311_arguments(BASE, 2048, 0x2004000, mutated) == N10_RT_INVALID);

    /* Builder size rule on the produced args: exactly 32 MiB accepted; one more page refused. */
    CHECK(builder_size_ok(n312_le64(args + N305_MEMSIZE)) && n312_le64(args + N305_MEMSIZE) - N311_KERNEL_OFFSET == BUILDER_MAX);
    CHECK(!builder_size_ok(0x3008000ULL) && !builder_size_ok(0x10000000ULL));

    /* Stub boot_args checks: v315 args accepted; memSize 0x10000000 (v314), image end above memSize, memSizeActual below
     * the window each park. */
    CHECK(stub_args_ok(args, BASE, IMAGE_BYTES));
    memcpy(mutated, args, sizeof(args));
    n306_put64(mutated + N305_MEMSIZE, 0x10000000ULL);
    CHECK(!stub_args_ok(mutated, BASE, IMAGE_BYTES));
    CHECK(!stub_args_ok(args, BASE, 0x2004000ULL));
    memcpy(mutated, args, sizeof(args));
    n306_put64(mutated + N305_MEMACTUAL, 0x3004000ULL);
    CHECK(!stub_args_ok(mutated, BASE, IMAGE_BYTES));
    CHECK(n312_le64(args + N305_MEMACTUAL) == N311_WINDOW_BYTES);
    if (checks != EXPECTED_CHECKS) {
        fprintf(stderr, "v315 fixture check count %d\n", checks);
        return 1;
    }
    puts("v315 crumb fixture PASS");
    return 0;
}
