/* SPDX-License-Identifier: GPL-2.0-only */
/* v317 host fixture (new cases only): the N317PS20 record tag, N317_SEED_BYTES and the 4096-byte ADT storage/max, n310_adt
 * with the /chosen random-seed property (public synthetic constant seed[i] = 1 + i % 255) after dram-size for a 14-byte and
 * a 64-byte compatible, the arena union layout, a C mirror of the Linux handoff copy, the enter hash refusal and the stub
 * handoff compare over a 2256-byte ADT, and the N317PS2T validator with the unchanged N315 crumbs. Synthetic values only:
 * synthetic window base, image size, compatible, cpu regs, frequency, DRAM span and record fields; no real kernel bytes,
 * entry, address or register. */
#include <stddef.h>
#include <stdio.h>
#include "v317_abi_contract.h"
#include "v317_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 32 MiB-aligned window base >= 2 GiB */
#define DRAM_BASE 0x80000000ULL      /* synthetic DRAM span containing the window */
#define DRAM_SIZE 0x40000000ULL
#define MPIDR 0x81000010ULL          /* synthetic raw MPIDR: affinity 0x10 */
#define FREQUENCY 26000000U          /* synthetic timebase */
#define ADT_NODES 13U
#define ADT_FNV 0xc1cb3618U          /* synthetic record field */
#define ARGS_FNV 0xaee810a3U         /* synthetic record field */
#define IMAGE_FNV 0x4e154d31U        /* synthetic image word-FNV (record field) */
#define IMAGE_TICKS 0x1234U          /* synthetic MMU-off hash ticks */
#define ENTRY 0x4010U                /* synthetic entry offset */
#define ENTRY_WORD 0x14000001U       /* synthetic 'b .+4' at the entry */
#define IMAGE_BYTES 0x1240000U       /* synthetic loaded-image size (16 KiB multiple) */
#define COMPAT14 "synthetic,n10"     /* 13 characters + NUL = 14 bytes */
#define COMPAT64 "synthetic,note10-compatible-string-of-sixty-three-characters-xx"
#define FIXTURE_GROUPS 6
#define FIXTURE_VARIANTS 20
#define EXPECTED_CHECKS 20
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

_Static_assert(N317_SEED_BYTES == 256, "random-seed length");
_Static_assert(N307_ADT_STORAGE == 4096 && N307_ADT_MAX_BYTES == 4096, "v317 ADT storage and max");
_Static_assert(2240 + N304_COMPAT_BYTES <= N307_ADT_STORAGE, "largest ADT fits the storage");
_Static_assert(N306_ADT_OFFSET + N307_ADT_STORAGE <= N316_HANDOFF_BYTES, "ADT copy fits the handoff page");
_Static_assert(sizeof(COMPAT14) == 14 && sizeof(COMPAT64) == N304_COMPAT_BYTES, "synthetic compatible lengths");

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v317 fixture failed at line %d\n", __LINE__); \
            return 1;                                                     \
        }                                                                 \
        ++checks;                                                         \
    } while (0)

static uint8_t arena_args[N304_ARGS_BYTES], arena_adt[N307_ADT_STORAGE], large_adt[N307_ADT_STORAGE];
static uint8_t page[N316_HANDOFF_BYTES], spare[N316_HANDOFF_BYTES];

/* Mirror of the v316 prepare copy (unchanged C): zero the page, args at +0, ADT at +N306_ADT_OFFSET. */
static void copy_to_handoff(uint8_t *out, uint32_t adt_bytes)
{
    memset(out, 0, N316_HANDOFF_BYTES);
    memcpy(out, arena_args, N304_ARGS_BYTES);
    memcpy(out + N306_ADT_OFFSET, arena_adt, adt_bytes);
}

/* Mirror of the v316 enter refusal on the copy (unchanged C): both FNVs equal the arena hashes. */
static int copy_hash_ok(const uint8_t *copy, uint32_t adt_bytes, uint32_t args_hash, uint32_t adt_hash)
{
    return n304_fnv(copy, N304_ARGS_BYTES) == args_hash && n304_fnv(copy + N306_ADT_OFFSET, adt_bytes) == adt_hash;
}

/* Mirror of the v316 stub handoff compare (unchanged stub): 32-bit words over [0, 1152), then [2048, 2048 + adt_bytes);
 * 1 = pass, 0 = park. The ADT max compare 'cmp w25, #N307_ADT_MAX_BYTES' precedes it. */
static int stub_handoff_ok(const uint8_t *arena, const uint8_t *copy, uint32_t adt_bytes)
{
    uint64_t x7 = 0, x8 = N304_ARGS_BYTES;

    if (adt_bytes < N306_ADT_MIN_BYTES || adt_bytes > N307_ADT_MAX_BYTES || adt_bytes % 4)
        return 0;
    for (;;) {
        do {
            if (n312_le32(arena + x7) != n312_le32(copy + x7))
                return 0;
            x7 += 4;
        } while (x7 < x8);
        if (x7 >= N306_ADT_OFFSET)
            return 1;
        x7 = N306_ADT_OFFSET;
        x8 = (uint64_t)adt_bytes + N306_ADT_OFFSET;
    }
}

/* /chosen random-seed property facts: key, length and value bytes 1 + i % 255 at the given property start. */
static int seed_ok(const uint8_t *adt, uint32_t at)
{
    static const char key[32] = "random-seed";
    uint32_t i;

    if (memcmp(adt + at, key, sizeof(key)) || n312_le32(adt + at + 32) != N317_SEED_BYTES)
        return 0;
    for (i = 0; i < N317_SEED_BYTES; ++i)
        if (adt[at + 36 + i] != (uint8_t)(1 + i % 255) || !adt[at + 36 + i])
            return 0;
    return adt[at + 36] == 1 && adt[at + 36 + 254] == 255 && adt[at + 36 + 255] == 1;
}

static void put_hex(char *field, size_t digits, uint64_t value)
{
    static const char hex[] = "0123456789abcdef";

    while (digits) {
        field[--digits] = hex[value & 15];
        value >>= 4;
    }
}

static void make_record(char *record, const char *tag)
{
    char text[N304_HOST_RECORD_BYTES + 1];

    snprintf(text, sizeof(text), N304_HOST_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID);
    memcpy(record, text, N304_HOST_RECORD_BYTES);
    memcpy(record, tag, 7);
    put_hex(record + N304_HOST_REG_OFFSET, 16, BASE);
    put_hex(record + N304_HOST_REG_OFFSET + N304_HOST_REG_STRIDE, 16, MPIDR);
    put_hex(record + N304_HOST_REG_OFFSET + 2 * N304_HOST_REG_STRIDE, 16, (uint64_t)IMAGE_TICKS << 32 | IMAGE_FNV);
    put_hex(record + N304_HOST_REG_OFFSET + 3 * N304_HOST_REG_STRIDE, 16, (uint64_t)ENTRY << 32 | ENTRY_WORD);
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
    static const char crumbs[] = "N315E1-\nN315B20\nN315M3-\n[0:";
    const uint64_t regs[N307_CPUS] = {0x10, 0x11, 0x12, 0x13, 0x100, 0x101, 0x200, 0x201}; /* synthetic */
    const uint64_t h = BASE + N311_KERNEL_OFFSET + IMAGE_BYTES;
    /* v316 /chosen layout for a 14-byte compatible: root node 8, name 48, compatible 36 + 16, chosen node 8, name 44,
     * then the dram-base value at +36. */
    const uint32_t dram_v316 = 8 + 48 + 36 + 16 + 8 + 44 + 36;
    uint8_t args[N304_ARGS_BYTES];
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10, .args_hash = ARGS_FNV,
                                                 .adt_hash = ADT_FNV, .adt_nodes = ADT_NODES, .image_hash = IMAGE_FNV,
                                                 .entry_offset = ENTRY, .entry_word = ENTRY_WORD};
    struct n310_offsets offsets, large_offsets;
    uint32_t adt_bytes, large_bytes, args_hash, adt_hash, chosen, seed;
    int code = -2;

    /* Group 1: kernel record format tag N317PS20 (static seed/storage constants above). */
    CHECK(snprintf(text, sizeof(text), N304_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_RECORD_BYTES &&
          !memcmp(text, "N317PS20", 8));

    /* Group 2: n310_adt with a 14-byte compatible and base H: 2256 bytes, /chosen nProps 4, random-seed after dram-size. */
    adt_bytes = n310_adt(arena_adt, COMPAT14, sizeof(COMPAT14), h, regs, N307_CPUS, FREQUENCY, DRAM_BASE, DRAM_SIZE, &offsets);
    chosen = 8 + 48 + 36 + 16;
    seed = offsets.dram + 8 + 44;
    CHECK(adt_bytes == 2256 && adt_bytes == 2240 + ((sizeof(COMPAT14) + 3) & ~3U));
    CHECK(n312_le32(arena_adt + chosen) == 4 && n312_le32(arena_adt + chosen + 4) == 1 &&
          !memcmp(arena_adt + chosen + 8, "name", 5));
    CHECK(offsets.dram == dram_v316 && n312_le64(arena_adt + offsets.dram) == DRAM_BASE &&
          n312_le64(arena_adt + offsets.dram + N309_DRAM_NAME_STRIDE) == DRAM_SIZE &&
          !memcmp(arena_adt + offsets.dram + 8, "dram-size", 10));
    CHECK(seed_ok(arena_adt, seed));
    CHECK(n312_le64(arena_adt + offsets.bootargs) == h && n312_le64(arena_adt + offsets.bootargs + 8) == N304_ARGS_BYTES &&
          n312_le64(arena_adt + offsets.devtree) == h + N306_ADT_OFFSET &&
          n312_le64(arena_adt + offsets.devtree + 8) == adt_bytes && offsets.bootargs > seed + 36 + N317_SEED_BYTES);
    CHECK(offsets.defaults + N310_DEFAULTS_NODE_BYTES == adt_bytes && n10_rt_validate_adt(arena_adt, adt_bytes) == N10_RT_OK);

    /* Group 3: n310_adt with the largest (64-byte) compatible: 2304 <= 4096 accepted and valid; a 65-byte count refused. */
    large_bytes = n310_adt(large_adt, COMPAT64, sizeof(COMPAT64), h, regs, N307_CPUS, FREQUENCY, DRAM_BASE, DRAM_SIZE,
                           &large_offsets);
    CHECK(large_bytes == 2240 + 64 && large_bytes <= N307_ADT_STORAGE);
    CHECK(n10_rt_validate_adt(large_adt, large_bytes) == N10_RT_OK && seed_ok(large_adt, large_offsets.dram + 8 + 44));
    CHECK(!n310_adt(large_adt, COMPAT64 "y", sizeof(COMPAT64) + 1, h, regs, N307_CPUS, FREQUENCY, DRAM_BASE, DRAM_SIZE,
                    &large_offsets));

    /* Group 4: arena union layout with the 4096-byte ADT storage. */
    CHECK(offsetof(union n304_storage, view.adt) == N306_ADT_OFFSET);
    CHECK(offsetof(union n304_storage, view.adt) + N307_ADT_STORAGE == 6144 && 6144 <= N316_HANDOFF_BYTES);
    CHECK(sizeof(union n304_storage) == N304_ARENA_BYTES && N304_ARENA_BYTES == 16384);

    /* Group 5: handoff copy mirror, enter refusal and stub handoff compare over the 2256-byte ADT. */
    CHECK(n311_arguments(BASE, adt_bytes, IMAGE_BYTES, args) == N10_RT_OK && n312_le32(args + 104) == adt_bytes);
    memcpy(arena_args, args, sizeof(args));
    args_hash = n304_fnv(arena_args, N304_ARGS_BYTES);
    adt_hash = n304_fnv(arena_adt, adt_bytes);
    memset(page, 0xa5, sizeof(page));
    copy_to_handoff(page, adt_bytes);
    memset(spare, 0, sizeof(spare));
    memcpy(spare, arena_args, N304_ARGS_BYTES);
    memcpy(spare + N306_ADT_OFFSET, arena_adt, adt_bytes);
    CHECK(!memcmp(page, spare, sizeof(page)) && copy_hash_ok(page, adt_bytes, args_hash, adt_hash));
    CHECK(stub_handoff_ok(spare, page, adt_bytes));
    page[N306_ADT_OFFSET + seed + 36 + 100] ^= 1; /* one flipped seed byte in the copy */
    CHECK(!copy_hash_ok(page, adt_bytes, args_hash, adt_hash));
    CHECK(!stub_handoff_ok(spare, page, adt_bytes));
    page[N306_ADT_OFFSET + seed + 36 + 100] ^= 1;

    /* Group 6: N317PS2T validator with the unchanged N315 crumbs; an N316PS2T record is not a v317 witness. */
    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    make_record(record, "N317PS2");
    CHECK(n306_host_record_valid(record, sizeof(record), &expected) &&
          n315_crumb_trace(crumbs, sizeof(crumbs) - 1, &code) == 7 && code == 0);
    make_record(altered, "N316PS2");
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));

    if (checks != EXPECTED_CHECKS || FIXTURE_VARIANTS != EXPECTED_CHECKS) {
        fprintf(stderr, "v317 fixture check count %d\n", checks);
        return 1;
    }
    puts("v317 seed fixture PASS");
    return 0;
}
