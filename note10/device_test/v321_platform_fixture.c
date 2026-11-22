/* SPDX-License-Identifier: GPL-2.0-only */
/* v321 host fixture (new cases only): n310_adt with the /chosen/note10-platform node (second /chosen child after memory-map:
 * compatible, version, gic-handoff, gic-reg, timer-intid, timebase-frequency) for a 14-byte compatible, the v321 ADT validator
 * (accepts the 'gic-handoff' property key, still rejects a node named 'gic-handoff'; the unchanged runtime_relocation.c
 * rejects the v321 ADT), a C mirror of the Linux handoff copy, the enter hash refusal and the stub handoff compare over the
 * 2608-byte ADT, and the N321PS2T validator with the unchanged N315 crumbs. Synthetic values only: synthetic window base,
 * image size, compatible, cpu regs, frequency, DRAM span and record fields; the GIC addresses and timer PPI are public SoC
 * contract constants; no real kernel bytes, entry, address or register. */
#include <stdio.h>
#include "v321_abi_contract.h"
#include "v321_host_record_validate.h"

/* The unchanged runtime_relocation.c (earlier builds), its functions renamed (function-like macros, so the struct tag
 * n10_rt_plan is untouched) so both validators link into this fixture. */
#define n10_rt_validate_adt(raw, size) v320_rt_validate_adt(raw, size)
#define n10_rt_plan(in, out) v320_rt_plan(in, out)
#define n10_rt_serialize_boot_args(f, out, capacity) v320_rt_serialize_boot_args(f, out, capacity)
#define n10_rt_serialize_record(args, entry, out, capacity) v320_rt_serialize_record(args, entry, out, capacity)
#define n10_rt_build(...) v320_rt_build(__VA_ARGS__)
#include "runtime_relocation.c"
#undef n10_rt_validate_adt
#undef n10_rt_plan
#undef n10_rt_serialize_boot_args
#undef n10_rt_serialize_record
#undef n10_rt_build

#define BASE 0x90000000ULL           /* synthetic 32 MiB-aligned window base >= 2 GiB */
#define DRAM_BASE 0x80000000ULL      /* synthetic DRAM span containing the window */
#define DRAM_SIZE 0x40000000ULL
#define MPIDR 0x81000010ULL          /* synthetic raw MPIDR: affinity 0x10 */
#define FREQUENCY 24000000U          /* synthetic timebase */
#define ADT_NODES 14U
#define ADT_FNV 0xc1cb3618U          /* synthetic record field */
#define ARGS_FNV 0xaee810a3U         /* synthetic record field */
#define IMAGE_FNV 0x4e154d31U        /* synthetic image word-FNV (record field) */
#define IMAGE_TICKS 0x1234U          /* synthetic MMU-off hash ticks */
#define ENTRY 0x4010U                /* synthetic entry offset */
#define ENTRY_WORD 0x14000001U       /* synthetic 'b .+4' at the entry */
#define IMAGE_BYTES 0x1240000U       /* synthetic loaded-image size (16 KiB multiple) */
#define COMPAT14 "synthetic,n10"     /* 13 characters + NUL = 14 bytes */
#define FIXTURE_GROUPS 4
#define FIXTURE_VARIANTS 14
#define EXPECTED_CHECKS 14
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

_Static_assert(sizeof(COMPAT14) == 14, "synthetic compatible length");
_Static_assert(2592 + N304_COMPAT_BYTES <= N307_ADT_STORAGE, "largest v321 ADT fits the storage");

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v321 fixture failed at line %d\n", __LINE__); \
            return 1;                                                     \
        }                                                                 \
        ++checks;                                                         \
    } while (0)

static uint8_t arena_args[N304_ARGS_BYTES], arena_adt[N307_ADT_STORAGE], small_adt[64];
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

/* Walked node count from the node at *at (header u32 nProps, u32 nChildren; property 32 + 4 + value padded to 4). */
static uint32_t walk_nodes(const uint8_t *adt, uint32_t *at)
{
    uint32_t props = n312_le32(adt + *at), children = n312_le32(adt + *at + 4), count = 1, i;

    *at += 8;
    for (i = 0; i < props; ++i)
        *at += 36 + ((n312_le32(adt + *at + 32) + 3) & ~3U);
    for (i = 0; i < children; ++i)
        count += walk_nodes(adt, at);
    return count;
}

/* Property at *at has this key, length and value; zero padding to 4. Advances *at. */
static int prop_is(const uint8_t *adt, uint32_t *at, const char *key, const void *value, uint32_t length)
{
    char name[32] = {0};
    uint32_t i, padded = (length + 3) & ~3U;

    for (i = 0; key[i]; ++i)
        name[i] = key[i];
    if (memcmp(adt + *at, name, sizeof(name)) || n312_le32(adt + *at + 32) != length ||
        memcmp(adt + *at + 36, value, length))
        return 0;
    for (i = length; i < padded; ++i)
        if (adt[*at + 36 + i])
            return 0;
    *at += 36 + padded;
    return 1;
}

/* The note10-platform node at `at`: header (7, 0) and the seven properties in order with exact values. */
static int platform_ok(const uint8_t *adt, uint32_t at, uint32_t frequency)
{
    uint8_t version[4], handoff[4], reg[32], intid[4], tbf[4];

    n306_put32(version, N321_PLATFORM_VERSION);
    n306_put32(handoff, 1);
    n306_put64(reg, N321_GICD_BASE);
    n306_put64(reg + 8, N321_GIC_SIZE);
    n306_put64(reg + 16, N321_GICC_BASE);
    n306_put64(reg + 24, N321_GIC_SIZE);
    n306_put32(intid, N321_TIMER_INTID);
    n306_put32(tbf, frequency);
    if (n312_le32(adt + at) != 7 || n312_le32(adt + at + 4) != 0)
        return 0;
    at += 8;
    return prop_is(adt, &at, "name", "note10-platform", 16) &&
           prop_is(adt, &at, "compatible", "samsung,exynos9825-note10", 26) &&
           prop_is(adt, &at, "version", version, 4) && prop_is(adt, &at, "gic-handoff", handoff, 4) &&
           prop_is(adt, &at, "gic-reg", reg, 32) && prop_is(adt, &at, "timer-intid", intid, 4) &&
           prop_is(adt, &at, "timebase-frequency", tbf, 4) && n312_le32(adt + at) == 1 && n312_le32(adt + at + 4) == 8 &&
           !memcmp(adt + at + 8, "name", 5) && !memcmp(adt + at + 44, "cpus", 5) &&
           N321_GICD_BASE == 0x10101000 && N321_GICC_BASE == 0x10102000 && N321_GIC_SIZE == 0x1000 &&
           N321_TIMER_INTID == 30 && N321_PLATFORM_VERSION == 1;
}

/* Minimal ADT: one root node with a single 'name' property (12-byte value, NUL-terminated). */
static uint32_t one_node(const char *name)
{
    uint32_t at;

    memset(small_adt, 0, sizeof(small_adt));
    at = n306_node(small_adt, 0, 1, 0);
    return n306_prop(small_adt, at, "name", name, 12);
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
    char text[N304_RECORD_BYTES + 1], host[N304_HOST_RECORD_BYTES + 1];
    char record[N304_HOST_RECORD_BYTES], altered[N304_HOST_RECORD_BYTES];
    static const char crumbs[] = "N315E1-\nN315B20\nN315M3-\n[0:";
    const uint64_t regs[N307_CPUS] = {0x10, 0x11, 0x12, 0x13, 0x100, 0x101, 0x200, 0x201}; /* synthetic */
    const uint64_t h = BASE + N311_KERNEL_OFFSET + IMAGE_BYTES;
    /* /chosen for a 14-byte compatible: root node 8, name 48, compatible 36 + 16. */
    const uint32_t chosen = 8 + 48 + 36 + 16;
    uint8_t args[N304_ARGS_BYTES];
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10, .args_hash = ARGS_FNV,
                                                 .adt_hash = ADT_FNV, .adt_nodes = ADT_NODES, .image_hash = IMAGE_FNV,
                                                 .entry_offset = ENTRY, .entry_word = ENTRY_WORD};
    struct n310_offsets offsets;
    uint32_t adt_bytes, args_hash, adt_hash, platform, walked = 0, nodes, gic;
    int code = -2;

    /* Group 1: n310_adt with a 14-byte compatible: 2608 bytes, /chosen nProps 4 / nChildren 2, the note10-platform node
     * right after memory-map (DeviceTree is its last property) with the seven properties in order, 14 nodes, root
     * nChildren 3 and /defaults last. */
    adt_bytes = n310_adt(arena_adt, COMPAT14, sizeof(COMPAT14), h, regs, N307_CPUS, FREQUENCY, DRAM_BASE, DRAM_SIZE, &offsets);
    platform = offsets.devtree + 16;
    CHECK(adt_bytes == 2608 && adt_bytes == 2592 + ((sizeof(COMPAT14) + 3) & ~3U) && adt_bytes <= N307_ADT_STORAGE);
    CHECK(n312_le32(arena_adt + chosen) == 4 && n312_le32(arena_adt + chosen + 4) == 2 &&
          !memcmp(arena_adt + chosen + 8, "name", 5) && !memcmp(arena_adt + chosen + 44, "chosen", 7) &&
          n312_le64(arena_adt + offsets.devtree) == h + N306_ADT_OFFSET && n312_le64(arena_adt + offsets.devtree + 8) == adt_bytes);
    CHECK(platform_ok(arena_adt, platform, FREQUENCY) && n312_le32(arena_adt + offsets.timebase) == FREQUENCY);
    nodes = walk_nodes(arena_adt, &walked);
    CHECK(nodes == ADT_NODES && walked == adt_bytes && n312_le32(arena_adt + 4) == 3 &&
          offsets.defaults + N310_DEFAULTS_NODE_BYTES == adt_bytes && !memcmp(arena_adt + offsets.defaults + 44, "defaults", 9));

    /* Group 2: the v321 validator accepts the ADT (gic-handoff key allowed) and still rejects a node named 'gic-handoff';
     * the unchanged runtime_relocation.c rejects the v321 ADT (intentional change). */
    CHECK(n10_rt_validate_adt(arena_adt, adt_bytes) == N10_RT_OK);
    CHECK(n10_rt_validate_adt(small_adt, one_node("gic-handoff")) == N10_RT_ADT &&
          n10_rt_validate_adt(small_adt, one_node("gic-handofg")) == N10_RT_OK);
    CHECK(v320_rt_validate_adt(arena_adt, adt_bytes) == N10_RT_ADT);

    /* Group 3: handoff copy mirror, enter refusal and stub handoff compare over the 2608-byte ADT; one flipped gic-reg byte
     * in the copy is refused and parks. */
    CHECK(n311_arguments(BASE, adt_bytes, IMAGE_BYTES, args) == N10_RT_OK && n312_le32(args + 104) == adt_bytes);
    memcpy(arena_args, args, sizeof(args));
    args_hash = n304_fnv(arena_args, N304_ARGS_BYTES);
    adt_hash = n304_fnv(arena_adt, adt_bytes);
    memset(page, 0xa5, sizeof(page));
    copy_to_handoff(page, adt_bytes);
    memset(spare, 0, sizeof(spare));
    memcpy(spare, arena_args, N304_ARGS_BYTES);
    memcpy(spare + N306_ADT_OFFSET, arena_adt, adt_bytes);
    CHECK(!memcmp(page, spare, sizeof(page)) && copy_hash_ok(page, adt_bytes, args_hash, adt_hash) &&
          stub_handoff_ok(spare, page, adt_bytes));
    gic = platform + 8 + 52 + 64 + 40 + 40 + 36 + 1; /* second byte of the gic-reg value (GICD base) */
    page[N306_ADT_OFFSET + gic] ^= 1;
    CHECK(!copy_hash_ok(page, adt_bytes, args_hash, adt_hash));
    CHECK(!stub_handoff_ok(spare, page, adt_bytes));
    page[N306_ADT_OFFSET + gic] ^= 1;

    /* Group 4: record format tags N321PS20 (length 250) and the N321PS2T validator with the unchanged N315 crumbs; an
     * N320PS2T record is not a v321 witness. */
    CHECK(snprintf(text, sizeof(text), N304_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_RECORD_BYTES &&
          snprintf(host, sizeof(host), N304_HOST_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_HOST_RECORD_BYTES &&
          N304_RECORD_BYTES == 250 && !memcmp(text, "N321PS20", 8) && !memcmp(text, host, sizeof(host)));
    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    make_record(record, "N321PS2");
    CHECK(n306_host_record_valid(record, sizeof(record), &expected) &&
          n315_crumb_trace(crumbs, sizeof(crumbs) - 1, &code) == 7 && code == 0);
    make_record(altered, "N320PS2");
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));

    if (checks != EXPECTED_CHECKS || FIXTURE_VARIANTS != EXPECTED_CHECKS || FIXTURE_GROUPS != 4) {
        fprintf(stderr, "v321 fixture check count %d\n", checks);
        return 1;
    }
    puts("v321 platform fixture PASS");
    return 0;
}
