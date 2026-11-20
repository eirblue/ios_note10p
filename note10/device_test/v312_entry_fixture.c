/* SPDX-License-Identifier: GPL-2.0-only */
/* v312 host fixture (new cases only): the n312_entry_offset LC_UNIXTHREAD parser, a C mirror of the new stub entry
 * block (r[3] = entry_offset << 32 | entry word) and the N312PS2T record validator. Synthetic values only: a 32 KiB
 * synthetic Mach-O image (one executable LC_SEGMENT_64 and one LC_UNIXTHREAD), no real kernel bytes or entry. */
#include <stdio.h>
#include "v312_abi_contract.h"
#include "v312_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 32 MiB-aligned window base >= 2 GiB */
#define MPIDR 0x81000010ULL          /* synthetic raw MPIDR: affinity 0x10 */
#define ADT_BYTES 1960U              /* synthetic ADT size (v311 fixture compatible) */
#define ADT_NODES 13U
#define ADT_FNV 0xc1cb3618U          /* v311 fixture ADT vector (record field only) */
#define ARGS_FNV 0xaee810a3U         /* n311_arguments(BASE, ADT_BYTES, IMAGE_BYTES) */
#define IMAGE_BYTES 32768U
#define IMAGE_FNV 0x4e154d31U        /* n311_fnv_words of the synthetic v312 image */
#define IMAGE_TICKS 0x1234U          /* synthetic MMU-off hash ticks */
#define SEG_OFF 32U                  /* LC_SEGMENT_64 command offset */
#define THREAD_OFF 104U              /* LC_UNIXTHREAD command offset */
#define ENTRY 0x4010U                /* synthetic entry offset */
#define ENTRY_WORD 0x14000001U       /* synthetic 'b .+4' at the entry */
#define EXPECTED_CHECKS 26
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

_Static_assert(offsetof(struct n304_metadata, entry_offset) == N312_META_ENTRY_OFFSET, "entry offset slot");
_Static_assert(offsetof(struct n304_metadata, image_bytes) == N311_META_IMAGE_BYTES, "image bytes slot");
_Static_assert(N312_LINK_BASE == N311_VIRT_BASE + N311_KERNEL_OFFSET, "link base");
_Static_assert(sizeof(struct n304_metadata) + N304_META_OFFSET <= N306_ADT_OFFSET, "metadata below ADT");
_Static_assert(sizeof(union n304_storage) == N304_ARENA_BYTES, "arena size");

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v312 fixture failed at line %d\n", __LINE__); \
            return 1;                                                     \
        }                                                                 \
        ++checks;                                                         \
    } while (0)

/* Mirror of the v312 stub entry block: meta entry_offset nonzero, 4-aligned, <= image_bytes - 4; r[3] value. */
static int entry_ok(const struct n304_metadata *meta, const uint8_t *image, uint64_t *r3)
{
    uint32_t entry = meta->entry_offset;

    if (!entry || entry % 4 || entry > meta->image_bytes - 4)
        return 0;
    *r3 = (uint64_t)entry << 32 | n312_le32(image + entry);
    return 1;
}

static int parse(const uint8_t *image, uint32_t *out)
{
    *out = 0;
    return n312_entry_offset(image, IMAGE_BYTES, out);
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
    static uint8_t image[IMAGE_BYTES], bad[IMAGE_BYTES], args[N304_ARGS_BYTES];
    static struct n304_metadata meta, other;
    uint32_t entry;
    uint64_t r3 = 0;
    char record[N304_HOST_RECORD_BYTES], altered[N304_HOST_RECORD_BYTES];
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10, .args_hash = ARGS_FNV,
                                                 .adt_hash = ADT_FNV, .adt_nodes = ADT_NODES, .image_hash = IMAGE_FNV,
                                                 .entry_offset = ENTRY, .entry_word = ENTRY_WORD},
                                     zero = expected;
    const struct {
        uint32_t offset; /* image byte offset of a 32-bit word */
        uint32_t value;
    } reject[] = {
        {THREAD_OFF, 4},                                        /* zero LC_UNIXTHREAD (LC_THREAD) */
        {THREAD_OFF + 8, 5},                                    /* flavor 5 */
        {THREAD_OFF + 12, 67},                                  /* count 67 */
        {20, 72 + 280},                                         /* thread command runs past sizeofcmds */
        {20, IMAGE_BYTES},                                      /* 32 + sizeofcmds > image_bytes */
        {THREAD_OFF + N312_THREAD_PC_OFFSET, (uint32_t)N312_LINK_BASE - 0x1000}, /* pc < link base */
        {THREAD_OFF + N312_THREAD_PC_OFFSET, (uint32_t)N312_LINK_BASE + 0x4012}, /* unaligned entry */
        {THREAD_OFF + N312_THREAD_PC_OFFSET, (uint32_t)N312_LINK_BASE + IMAGE_BYTES - 2}, /* entry image_bytes-2 */
        {SEG_OFF + 60, 3},                                      /* pc segment initprot 3 (no execute) */
        {THREAD_OFF + N312_THREAD_PC_OFFSET, (uint32_t)N312_LINK_BASE + 0x3ff0}, /* pc outside every segment */
    };
    const uint32_t meta_reject[] = {0, 2, IMAGE_BYTES - 2, IMAGE_BYTES};

    /* Synthetic image: v311 word pattern, then a zeroed load-command region with one LC_SEGMENT_64 and one LC_UNIXTHREAD. */
    for (uint32_t i = 0; i < IMAGE_BYTES / 4; ++i)
        n306_put32(image + 4 * i, i * 0x9e3779b1U);
    memset(image + 16, 0, THREAD_OFF + N312_THREAD_CMD_MIN - 16);
    n306_put32(image, N311_MH_MAGIC);
    n306_put32(image + 4, N311_MH_CPU_ARM64);
    n306_put32(image + 8, 0);
    n306_put32(image + 12, N311_MH_EXECUTE);
    n306_put32(image + 16, 2);                                  /* ncmds */
    n306_put32(image + 20, N312_SEGMENT_CMD_MIN + N312_THREAD_CMD_MIN); /* sizeofcmds */
    n306_put32(image + SEG_OFF, N312_LC_SEGMENT_64);
    n306_put32(image + SEG_OFF + 4, N312_SEGMENT_CMD_MIN);
    n306_put64(image + SEG_OFF + 24, N312_LINK_BASE + 0x4000);  /* vmaddr */
    n306_put64(image + SEG_OFF + 32, 0x4000);                   /* vmsize */
    n306_put32(image + SEG_OFF + 60, 5);                        /* initprot r-x */
    n306_put32(image + THREAD_OFF, N312_LC_UNIXTHREAD);
    n306_put32(image + THREAD_OFF + 4, N312_THREAD_CMD_MIN);
    n306_put32(image + THREAD_OFF + 8, N312_THREAD_FLAVOR);
    n306_put32(image + THREAD_OFF + 12, N312_THREAD_COUNT);
    n306_put64(image + THREAD_OFF + N312_THREAD_PC_OFFSET, N312_LINK_BASE + ENTRY);
    n306_put32(image + ENTRY, ENTRY_WORD);

    /* Vectors recomputed for this image. */
    CHECK(n311_fnv_words(image, IMAGE_BYTES / 4) == IMAGE_FNV);
    CHECK(n311_arguments(BASE, ADT_BYTES, IMAGE_BYTES, args) == N10_RT_OK && n304_fnv(args, N304_ARGS_BYTES) == ARGS_FNV);

    /* Parser. */
    CHECK(parse(image, &entry) == 0 && entry == ENTRY && n312_le32(image + entry) == ENTRY_WORD);
    for (size_t i = 0; i < sizeof(reject) / sizeof(reject[0]); ++i) {
        memcpy(bad, image, sizeof(bad));
        n306_put32(bad + reject[i].offset, reject[i].value);
        CHECK(parse(bad, &entry) != 0 && entry == 0);
    }
    memcpy(bad, image, sizeof(bad));                            /* two LC_UNIXTHREAD */
    memcpy(bad + THREAD_OFF + N312_THREAD_CMD_MIN, image + THREAD_OFF, N312_THREAD_CMD_MIN);
    n306_put32(bad + 16, 3);
    n306_put32(bad + 20, N312_SEGMENT_CMD_MIN + 2 * N312_THREAD_CMD_MIN);
    CHECK(parse(bad, &entry) != 0 && entry == 0);
    memcpy(bad, image, sizeof(bad));                            /* thread cmdsize 280 (consistent sizeofcmds) */
    n306_put32(bad + THREAD_OFF + 4, 280);
    n306_put32(bad + 20, N312_SEGMENT_CMD_MIN + 280);
    CHECK(parse(bad, &entry) != 0 && entry == 0);
    memcpy(bad, image, sizeof(bad));                            /* thread cmdsize 292: not a multiple of 8 */
    n306_put32(bad + THREAD_OFF + 4, 292);
    n306_put32(bad + 20, N312_SEGMENT_CMD_MIN + 292);
    CHECK(parse(bad, &entry) != 0 && entry == 0);

    /* Stub entry block mirror. */
    meta.image_bytes = IMAGE_BYTES;
    meta.entry_offset = ENTRY;
    CHECK(entry_ok(&meta, image, &r3) && r3 == ((uint64_t)ENTRY << 32 | ENTRY_WORD));
    for (size_t i = 0; i < sizeof(meta_reject) / sizeof(meta_reject[0]); ++i) {
        other = meta;
        other.entry_offset = meta_reject[i];
        CHECK(!entry_ok(&other, image, &r3));
    }

    /* N312PS2T record validator. */
    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    zero = expected;
    zero.entry_offset = 0;
    make_record(record, "N312PS2", (uint64_t)ENTRY << 32 | ENTRY_WORD);
    CHECK(n306_host_record_valid(record, sizeof(record), &expected));
    make_record(altered, "N312PS2", (uint64_t)(ENTRY + 4) << 32 | ENTRY_WORD);   /* wrong offset */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, "N312PS2", (uint64_t)ENTRY << 32 | (ENTRY_WORD ^ 1));   /* wrong word */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, "N312PS2", ENTRY_WORD);                                 /* offset 0 */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &zero));
    make_record(altered, "N311PS2", (uint64_t)ENTRY << 32 | ENTRY_WORD);         /* N311 tag */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    if (checks != EXPECTED_CHECKS) {
        fprintf(stderr, "v312 fixture check count %d\n", checks);
        return 1;
    }
    puts("v312 entry fixture PASS");
    return 0;
}
