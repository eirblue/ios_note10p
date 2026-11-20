/* SPDX-License-Identifier: GPL-2.0-only */
/* v306 host fixture: multi-node ADT, boot_args at the new ADT offset, a C mirror of the stub
 * walker/offset/cross-check predicate, and the N306PS2T record validator. Synthetic values only. */
#include <stdio.h>
#include "v306_abi_contract.h"
#include "v306_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 16 KiB-aligned base */
#define COMPATIBLE "n10,fixture"     /* synthetic root compatible */
#define MPIDR 0x81000102ULL          /* synthetic raw MPIDR: affinity 0x102 */
#define REG 0x102U
#define FREQUENCY 19200000U          /* synthetic CNTFRQ */
#define MMFR0 0x0000000000101122ULL  /* synthetic observational value */
#define ADT_BYTES 424U
#define ADT_FNV 0x456dcbacU
#define ARGS_FNV 0xda4467aeU
#define REG_OFFSET 336U
#define TBF_OFFSET 376U
#define EXPECTED_CHECKS 30
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

_Static_assert(offsetof(struct n304_metadata, cpu_reg_offset) == N306_META_REG_OFF, "reg offset slot");
_Static_assert(offsetof(struct n304_metadata, timebase_offset) == N306_META_TBF_OFF, "tbf offset slot");
_Static_assert(offsetof(union n304_storage, view.meta) == N304_META_OFFSET, "meta offset");
_Static_assert(offsetof(union n304_storage, view.adt) == N306_ADT_OFFSET, "adt offset");
_Static_assert(sizeof(union n304_storage) == N304_ARENA_BYTES, "arena size");
_Static_assert(offsetof(struct n10_rt_boot_layout, Video) == N306_VIDEO, "Video");
_Static_assert(offsetof(struct n10_rt_boot_layout, deviceTreeP) == 96, "deviceTreeP");
_Static_assert(N306_ADT_MAX_BYTES / 4 <= 0xff, "n= fits two hex digits");

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v306 fixture failed at line %d\n", __LINE__); \
            return 1;                                                     \
        }                                                                 \
        ++checks;                                                         \
    } while (0)

static uint32_t rd32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static uint64_t rd64(const uint8_t *p)
{
    return (uint64_t)rd32(p) | (uint64_t)rd32(p + 4) << 32;
}

/* Mirror of the v306 stub additions (deviceTree pointer/length, Video, walk, offsets, cross-checks). */
static int entry_ok(const uint8_t *arena, uint32_t size, uint32_t reg_offset, uint32_t tbf_offset,
                    uint64_t mpidr, uint64_t frequency)
{
    const uint8_t *adt = arena + N306_ADT_OFFSET, *name;
    uint64_t at = 0, pending = 1, nodes = 0, end;
    uint32_t props, children, reg, tbf;

    if (size < N306_ADT_MIN_BYTES || size > N306_ADT_MAX_BYTES || size % 4 ||
        rd64(arena + 96) != BASE + N306_ADT_OFFSET || rd32(arena + 104) != size)
        return 0;
    for (int i = 0; i < 6; ++i)
        if (rd64(arena + N306_VIDEO + 8 * i))
            return 0;
    while (pending) {
        pending--;
        if (++nodes > 32 || at + 8 > size)
            return 0;
        props = rd32(adt + at);
        children = rd32(adt + at + 4);
        at += 8;
        if (!props || props > 32 || children > 32)
            return 0;
        pending += children;
        while (props--) {
            if (at + 36 > size || !adt[at] || adt[at + 31])
                return 0;
            end = at + 36 + (((uint64_t)rd32(adt + at + 32) + 3) & ~3ULL);
            if (end > size)
                return 0;
            at = end;
        }
    }
    if (at != size)
        return 0;
    if (reg_offset % 4 || reg_offset < 36 || reg_offset + 4ULL > size ||
        tbf_offset % 4 || tbf_offset < 36 || tbf_offset + 4ULL > size)
        return 0;
    name = adt + reg_offset - 36;
    if (memcmp(name, "reg\0", 4) || rd32(name + 32) != 4)
        return 0;
    reg = rd32(name + 36);
    name = adt + tbf_offset - 36;
    if (memcmp(name, "timebase", 8) || rd32(name + 32) != 4)
        return 0;
    tbf = rd32(name + 36);
    return (mpidr & N306_MPIDR_MASK) == reg && (uint32_t)frequency == tbf;
}

static void put_hex(char *field, size_t digits, uint64_t value)
{
    static const char hex[] = "0123456789abcdef";

    while (digits) {
        field[--digits] = hex[value & 15];
        value >>= 4;
    }
}

static void make_record(char *record, uint64_t mpidr, uint32_t args, uint32_t adt, uint32_t words)
{
    char text[N304_HOST_RECORD_BYTES + 1];

    snprintf(text, sizeof(text), N304_HOST_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID);
    memcpy(record, text, N304_HOST_RECORD_BYTES);
    put_hex(record + N304_HOST_REG_OFFSET, 16, BASE);
    put_hex(record + N304_HOST_REG_OFFSET + N304_HOST_REG_STRIDE, 16, mpidr);
    put_hex(record + N304_HOST_REG_OFFSET + 2 * N304_HOST_REG_STRIDE, 16, MMFR0);
    put_hex(record + N304_HOST_ARGS_HASH_OFFSET, 8, args);
    put_hex(record + N304_HOST_ADT_HASH_OFFSET, 8, adt);
    put_hex(record + N304_HOST_ADT_LENGTH_OFFSET, 2, words);
    put_hex(record + N304_HOST_SCTLR_OFFSET, 16, 0x30d00800);
    record[N304_HOST_EL_OFFSET] = '1';
    record[N304_HOST_DAIF_OFFSET] = 'f';
    record[N304_HOST_COMMIT_OFFSET] = N304_HOST_COMMITTED;
    put_hex(record + N304_HOST_CSUM_OFFSET, 8, n306_host_body_checksum(record));
}

int main(void)
{
    static union n304_storage good, bad;
    uint8_t *adt = good.view.adt;
    uint32_t reg_offset = 0, tbf_offset = 0, size, args_fnv;
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = REG};
    char record[N304_HOST_RECORD_BYTES], altered[N304_HOST_RECORD_BYTES];
    const struct {
        uint32_t offset; /* within the ADT unless video */
        uint32_t value;
        int video;
    } word_mutation[] = {
        {0, 1, 1},                     /* Video nonzero */
        {0, 0, 0},                     /* root nProps 0 */
        {4, 33, 0},                    /* root nChildren 33 */
        {160, 2, 0},                   /* cpus nChildren 2: missing child */
        {REG_OFFSET - 4, 8, 0},        /* reg length 8: properties overrun */
        {TBF_OFFSET - 4, 2, 0},        /* timebase length 2: tbf length != 4 */
        {REG_OFFSET - 36, 0x00676578, 0}, /* reg name "xeg" */
    };

    size = n306_adt(adt, COMPATIBLE, sizeof(COMPATIBLE), REG, FREQUENCY, &reg_offset, &tbf_offset);
    CHECK(size == ADT_BYTES && reg_offset == REG_OFFSET && tbf_offset == TBF_OFFSET);
    CHECK(n304_fnv(adt, size) == ADT_FNV);
    CHECK(n10_rt_validate_adt(adt, size) == N10_RT_OK);
    CHECK(n304_arguments(BASE, size, good.view.args) == N10_RT_OK);
    args_fnv = n304_fnv(good.view.args, N304_ARGS_BYTES);
    CHECK(args_fnv == ARGS_FNV);
    CHECK(rd64(good.view.args + 96) == BASE + N306_ADT_OFFSET && rd32(good.view.args + 104) == size);
    CHECK(entry_ok(good.arena, size, reg_offset, tbf_offset, MPIDR, FREQUENCY));

    for (size_t i = 0; i < sizeof(word_mutation) / sizeof(word_mutation[0]); ++i) {
        bad = good;
        n306_put32((word_mutation[i].video ? bad.view.args + N306_VIDEO : bad.view.adt) + word_mutation[i].offset,
                   word_mutation[i].value);
        CHECK(!entry_ok(bad.arena, size, reg_offset, tbf_offset, MPIDR, FREQUENCY));
    }
    CHECK(!entry_ok(good.arena, size - 4, reg_offset, tbf_offset, MPIDR, FREQUENCY)); /* truncated property */
    bad = good;
    bad.view.adt[8 + 31] = 'x';                                                    /* name[31] nonzero */
    CHECK(!entry_ok(bad.arena, size, reg_offset, tbf_offset, MPIDR, FREQUENCY));
    bad = good;
    n306_put32(bad.view.args + 104, size + 4);                                     /* trailing word */
    CHECK(!entry_ok(bad.arena, size + 4, reg_offset, tbf_offset, MPIDR, FREQUENCY));
    CHECK(!entry_ok(good.arena, size, reg_offset + 2, tbf_offset, MPIDR, FREQUENCY)); /* misaligned */
    CHECK(!entry_ok(good.arena, size, size, tbf_offset, MPIDR, FREQUENCY));            /* out of range */
    CHECK(!entry_ok(good.arena, size, reg_offset, tbf_offset, MPIDR + 1, FREQUENCY));  /* MPIDR mismatch */
    CHECK(!entry_ok(good.arena, size, reg_offset, tbf_offset, MPIDR, FREQUENCY + 1));  /* CNTFRQ mismatch */
    CHECK(entry_ok(good.arena, size, reg_offset, tbf_offset, MPIDR | 0xff000000ULL, FREQUENCY)); /* masked bits */

    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    expected.args_hash = args_fnv;
    expected.adt_hash = ADT_FNV;
    expected.adt_words = size / 4;
    make_record(record, MPIDR, args_fnv, ADT_FNV, size / 4);
    CHECK(n306_host_record_valid(record, sizeof(record), &expected));
    make_record(altered, MPIDR, args_fnv ^ 1, ADT_FNV, size / 4);
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, MPIDR, args_fnv, ADT_FNV ^ 1, size / 4);
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, MPIDR, args_fnv, ADT_FNV, size / 4 + 1);
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, MPIDR + 1, args_fnv, ADT_FNV, size / 4);
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    memcpy(altered, record, sizeof(record));
    altered[3] = '4';                                                              /* N304 tag */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    memcpy(altered, record, sizeof(record));
    altered[N304_HOST_COMMIT_OFFSET] = N304_HOST_PENDING;
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    memcpy(altered, record, sizeof(record));
    altered[N304_HOST_CSUM_OFFSET] ^= 1;
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    if (checks != EXPECTED_CHECKS) {
        fprintf(stderr, "v306 fixture check count %d\n", checks);
        return 1;
    }
    puts("v306 adt fixture PASS");
    return 0;
}
