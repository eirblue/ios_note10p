/* SPDX-License-Identifier: GPL-2.0-only */
/* v310 host fixture (v309 entry predicates carried forward, N310PS2T record): eight-CPU, memory-map ADT with
 * /chosen dram-base/dram-size and a root-level /defaults node, boot_args at the ADT offset, a C mirror of the stub
 * walker/memory-map/DRAM-span/defaults/cpu0 predicate, and the N310PS2T record validator. Synthetic values only. */
#include <stdio.h>
#include "v310_abi_contract.h"
#include "v310_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 16 KiB-aligned base */
#define COMPATIBLE "n10,fixture"     /* synthetic root compatible */
#define MPIDR 0x81000010ULL          /* synthetic raw MPIDR: affinity 0x10 */
#define FREQUENCY 19200000U          /* synthetic CNTFRQ */
#define MMFR0 0x0000000000101122ULL  /* synthetic observational value */
#define DRAM_BASE 0x40000000ULL      /* synthetic DRAM span start */
#define DRAM_SIZE 0x100000000ULL     /* synthetic DRAM span size */
#define ADT_BYTES 1960U
#define ADT_NODES 13U
#define ADT_FNV 0xc1cb3618U
#define ARGS_FNV 0xdc9df0dcU
#define OFF_DRAM 192U
#define OFF_BOOTARGS 336U
#define OFF_DEVTREE 388U
#define OFF_REG 584U
#define OFF_TBF 624U
#define OFF_DEFAULTS 1904U /* ADT_BYTES - N310_DEFAULTS_NODE_BYTES */
#define OFF_CPU0 (OFF_DEVTREE + 16U + 52U) /* cpus node header + name property */
#define EXPECTED_CHECKS 61
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

_Static_assert(offsetof(struct n304_metadata, cpu_reg_offset) == N306_META_REG_OFF, "reg offset slot");
_Static_assert(offsetof(struct n304_metadata, timebase_offset) == N306_META_TBF_OFF, "tbf offset slot");
_Static_assert(offsetof(struct n304_metadata, bootargs_map_offset) == N307_META_BOOTARGS_OFF, "BootArgs slot");
_Static_assert(offsetof(struct n304_metadata, devtree_map_offset) == N307_META_DEVTREE_OFF, "DeviceTree slot");
_Static_assert(offsetof(struct n304_metadata, dram_base_offset) == N309_META_DRAM_OFF, "dram-base slot");
_Static_assert(offsetof(struct n304_metadata, defaults_offset) == N310_META_DEFAULTS_OFF, "defaults slot");
_Static_assert(sizeof(struct n304_metadata) + N304_META_OFFSET <= N306_ADT_OFFSET, "metadata below ADT");
_Static_assert(offsetof(union n304_storage, view.meta) == N304_META_OFFSET, "meta offset");
_Static_assert(offsetof(union n304_storage, view.adt) == N306_ADT_OFFSET, "adt offset");
_Static_assert(N306_ADT_OFFSET + N307_ADT_STORAGE <= N304_ARENA_BYTES, "adt inside arena");
_Static_assert(sizeof(union n304_storage) == N304_ARENA_BYTES, "arena size");

static const uint64_t regs[N307_CPUS] = {0x10, 0x11, 0x12, 0x13, 0x110, 0x111, 0x210, 0x211};
static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v310 fixture failed at line %d\n", __LINE__); \
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

static int map_ok(const uint8_t *adt, uint32_t size, uint32_t offset, const char *prefix,
                  uint64_t address, uint64_t length)
{
    return !(offset % 4) && offset >= 36 && offset + 16ULL <= size && rd32(adt + offset - 4) == 16 &&
           !memcmp(adt + offset - 36, prefix, 8) && rd64(adt + offset) == address &&
           rd64(adt + offset + 8) == length;
}

/* Mirror of the v309 stub /chosen DRAM predicate: structure, nonzero non-wrapping span containing the arena. */
static int dram_ok(const uint8_t *adt, uint32_t size, uint32_t offset, uint64_t x0)
{
    uint64_t base, span;

    if (offset % 4 || offset < 36 || offset + (N309_DRAM_NAME_STRIDE + 8ULL) > size ||
        rd32(adt + offset - 4) != 8 || memcmp(adt + offset - 36, "dram-bas", 8) ||
        rd32(adt + offset + N309_DRAM_NAME_STRIDE - 4) != 8 || memcmp(adt + offset + 8, "dram-siz", 8))
        return 0;
    base = rd64(adt + offset);
    span = rd64(adt + offset + N309_DRAM_NAME_STRIDE);
    return span && base + span >= base && base <= x0 && x0 + N304_ARENA_BYTES <= base + span;
}

/* Mirror of the v310 stub /defaults predicate: root nChildren 3 and a 56-byte /defaults{name="defaults"} node
 * (nProps 1, nChildren 0) ending exactly at adt_bytes. */
static int defaults_ok(const uint8_t *adt, uint32_t size, uint32_t offset)
{
    const uint8_t *node = adt + offset;

    return rd32(adt + 4) == 3 && offset + (uint64_t)N310_DEFAULTS_NODE_BYTES == size && !(offset % 4) &&
           rd32(node) == 1 && rd32(node + 4) == 0 && !memcmp(node + 8, "name", 4) && rd32(node + 12) == 0 &&
           rd32(node + 40) == 9 && !memcmp(node + 44, "defaults", 8) && rd32(node + 52) == 0;
}

/* Mirror of the v306-v310 stub ADT predicates; returns the walked node count, or 0 on park. */
static uint32_t entry_nodes(const union n304_storage *arena, uint32_t size, uint64_t mpidr, uint64_t frequency)
{
    const uint8_t *adt = arena->view.adt, *name;
    const struct n304_metadata *meta = &arena->view.meta;
    uint64_t at = 0, pending = 1, nodes = 0, end;
    uint32_t props, children, reg, tbf;

    if (size < N306_ADT_MIN_BYTES || size > N307_ADT_MAX_BYTES || size % 4 ||
        rd64(arena->view.args + 96) != BASE + N306_ADT_OFFSET || rd32(arena->view.args + 104) != size)
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
    if (at != size ||
        !map_ok(adt, size, meta->bootargs_map_offset, "BootArgs", BASE, N304_ARGS_BYTES) ||
        !map_ok(adt, size, meta->devtree_map_offset, "DeviceTr", BASE + N306_ADT_OFFSET, size) ||
        !dram_ok(adt, size, meta->dram_base_offset, BASE) ||
        !defaults_ok(adt, size, meta->defaults_offset))
        return 0;
    if (meta->cpu_reg_offset % 4 || meta->cpu_reg_offset < 36 || meta->cpu_reg_offset + 4ULL > size ||
        meta->timebase_offset % 4 || meta->timebase_offset < 36 || meta->timebase_offset + 4ULL > size)
        return 0;
    name = adt + meta->cpu_reg_offset - 36;
    if (memcmp(name, "reg\0", 4) || rd32(name + 32) != 4)
        return 0;
    reg = rd32(name + 36);
    name = adt + meta->timebase_offset - 36;
    if (memcmp(name, "timebase", 8) || rd32(name + 32) != 4)
        return 0;
    tbf = rd32(name + 36);
    return (mpidr & N306_MPIDR_MASK) == reg && (uint32_t)frequency == tbf ? (uint32_t)nodes : 0;
}

static void put_hex(char *field, size_t digits, uint64_t value)
{
    static const char hex[] = "0123456789abcdef";

    while (digits) {
        field[--digits] = hex[value & 15];
        value >>= 4;
    }
}

static void make_record(char *record, uint32_t args, uint32_t adt, uint32_t nodes, uint64_t dram_size)
{
    char text[N304_HOST_RECORD_BYTES + 1];

    snprintf(text, sizeof(text), N304_HOST_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID);
    memcpy(record, text, N304_HOST_RECORD_BYTES);
    put_hex(record + N304_HOST_REG_OFFSET, 16, BASE);
    put_hex(record + N304_HOST_REG_OFFSET + N304_HOST_REG_STRIDE, 16, MPIDR);
    put_hex(record + N304_HOST_REG_OFFSET + 2 * N304_HOST_REG_STRIDE, 16, MMFR0);
    put_hex(record + N304_HOST_REG_OFFSET + 3 * N304_HOST_REG_STRIDE, 16, dram_size);
    put_hex(record + N304_HOST_ARGS_HASH_OFFSET, 8, args);
    put_hex(record + N304_HOST_ADT_HASH_OFFSET, 8, adt);
    put_hex(record + N304_HOST_ADT_LENGTH_OFFSET, 2, nodes);
    put_hex(record + N304_HOST_SCTLR_OFFSET, 16, 0x30d00800);
    record[N304_HOST_EL_OFFSET] = '1';
    record[N304_HOST_DAIF_OFFSET] = 'f';
    record[N304_HOST_COMMIT_OFFSET] = N304_HOST_COMMITTED;
    put_hex(record + N304_HOST_CSUM_OFFSET, 8, n306_host_body_checksum(record));
}

static uint32_t generate(uint8_t *out, const uint64_t *values, uint32_t cpus, uint64_t dram_base, uint64_t dram_size,
                         struct n310_offsets *offsets)
{
    return n310_adt(out, COMPATIBLE, sizeof(COMPATIBLE), BASE, values, cpus, FREQUENCY, dram_base, dram_size, offsets);
}

int main(void)
{
    static union n304_storage good, bad;
    static uint8_t scratch[N307_ADT_STORAGE];
    struct n310_offsets offsets, other;
    uint64_t wide[N307_CPUS];
    uint32_t size;
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10, .dram_size = DRAM_SIZE};
    char record[N304_HOST_RECORD_BYTES], altered[N304_HOST_RECORD_BYTES];
    const struct {
        uint32_t offset; /* ADT-relative byte offset of a 32-bit word */
        uint32_t value;
    } word_mutation[] = {
        {OFF_BOOTARGS, (uint32_t)BASE + 0x4000},       /* BootArgs paddr off by 0x4000 */
        {OFF_BOOTARGS + 8, N304_ARGS_BYTES - 1},       /* BootArgs length 1151 */
        {OFF_DEVTREE + 8, ADT_BYTES - 4},              /* DeviceTree length != adt_bytes */
        {OFF_DEVTREE, (uint32_t)BASE + 0x1000},        /* DeviceTree paddr wrong */
        {OFF_BOOTARGS - 4, 8},                         /* map length word 8 */
        {OFF_DEVTREE - 36, 0x69766566},                /* map name "fevi..." */
        {OFF_DRAM - 4, 4},                             /* dram-base length word 4 */
        {OFF_DRAM + N309_DRAM_NAME_STRIDE - 4, 16},    /* dram-size length word 16 */
        {OFF_DRAM - 32, 0x7361622e},                   /* name "dram.bas" */
        {OFF_DRAM + 12, 0x7a69732e},                   /* name "dram.siz" */
    };
    const struct {
        uint64_t base, span; /* written over the dram-base/dram-size values */
    } span_mutation[] = {
        {DRAM_BASE, 0},                                /* size value 0 */
        {BASE + 0x4000, DRAM_SIZE},                    /* base > x0 */
        {DRAM_BASE, BASE - DRAM_BASE},                 /* end < x0 + 16384 */
        {DRAM_BASE, 0 - DRAM_BASE},                    /* base + size wraps */
    };
    const uint32_t bad_offset[] = {
        OFF_DRAM + 2,                                  /* misaligned meta offset */
        32,                                            /* offset < 36 */
        ADT_BYTES - N309_DRAM_NAME_STRIDE - 4,         /* offset + 52 > adt_bytes */
    };
    const struct {
        uint32_t offset; /* ADT-relative byte offset of a 32-bit word in the /defaults node or root header */
        uint32_t value;
    } defaults_mutation[] = {
        {4, 2},                                        /* root nChildren 2 */
        {OFF_DEFAULTS, 2},                             /* nProps 2 */
        {OFF_DEFAULTS + 4, 1},                         /* nChildren 1 */
        {OFF_DEFAULTS + 8, 0x666d616e},                /* key "namf" */
        {OFF_DEFAULTS + 12, 1},                        /* nonzero key word at +12 */
        {OFF_DEFAULTS + 40, 8},                        /* length 8 */
        {OFF_DEFAULTS + 40, 10},                       /* length 10 */
        {OFF_DEFAULTS + 44, 0x62666564},               /* value "defb" */
        {OFF_DEFAULTS + 48, 0x74746c75},               /* value "ultt" */
        {OFF_DEFAULTS + 52, 0x100},                    /* nonzero word at +52 */
    };
    const uint32_t bad_defaults_offset[] = {
        OFF_DEFAULTS + 2,                              /* misaligned meta offset */
        OFF_DEFAULTS - 4,                              /* offset + 56 == adt_bytes - 4 */
        OFF_DEFAULTS + 4,                              /* offset + 56 == adt_bytes + 4 */
    };
    static const uint8_t defaults_node[N310_DEFAULTS_NODE_BYTES] = {
        1, 0, 0, 0, 0, 0, 0, 0, 'n', 'a', 'm', 'e', [40] = 9, [44] = 'd', 'e', 'f', 'a', 'u', 'l', 't', 's'
    };
    const struct {
        uint64_t base, span; /* generator inputs that must be rejected */
    } generator_reject[] = {
        {DRAM_BASE, 0},                                /* size 0 */
        {DRAM_BASE + 0x2000, DRAM_SIZE},               /* base unaligned */
        {DRAM_BASE, DRAM_SIZE + 0x2000},               /* size unaligned */
        {DRAM_BASE, 0 - DRAM_BASE},                    /* base + size overflow */
        {BASE + 0x4000, DRAM_SIZE},                    /* arena below base */
        {DRAM_BASE, BASE - DRAM_BASE},                 /* arena end past DRAM end */
    };

    size = generate(good.view.adt, regs, N307_CPUS, DRAM_BASE, DRAM_SIZE, &offsets);
    CHECK(size == ADT_BYTES && offsets.dram == OFF_DRAM && offsets.bootargs == OFF_BOOTARGS &&
          offsets.devtree == OFF_DEVTREE && offsets.reg == OFF_REG && offsets.timebase == OFF_TBF &&
          offsets.defaults == OFF_DEFAULTS && offsets.defaults == size - N310_DEFAULTS_NODE_BYTES);
    CHECK(rd32(good.view.adt + 4) == 3 && !memcmp(good.view.adt + OFF_DEFAULTS, defaults_node, sizeof(defaults_node)));
    CHECK(rd64(good.view.adt + OFF_DRAM) == DRAM_BASE &&
          rd64(good.view.adt + OFF_DRAM + N309_DRAM_NAME_STRIDE) == DRAM_SIZE);
    CHECK(n304_fnv(good.view.adt, size) == ADT_FNV);
    CHECK(n10_rt_validate_adt(good.view.adt, size) == N10_RT_OK);
    CHECK(n304_arguments(BASE, size, good.view.args) == N10_RT_OK);
    CHECK(n304_fnv(good.view.args, N304_ARGS_BYTES) == ARGS_FNV);
    good.view.meta.cpu_reg_offset = offsets.reg;
    good.view.meta.timebase_offset = offsets.timebase;
    good.view.meta.bootargs_map_offset = offsets.bootargs;
    good.view.meta.devtree_map_offset = offsets.devtree;
    good.view.meta.dram_base_offset = offsets.dram;
    good.view.meta.defaults_offset = offsets.defaults;
    CHECK(entry_nodes(&good, size, MPIDR, FREQUENCY) == ADT_NODES);

    for (size_t i = 0; i < sizeof(word_mutation) / sizeof(word_mutation[0]); ++i) {
        bad = good;
        n306_put32(bad.view.adt + word_mutation[i].offset, word_mutation[i].value);
        CHECK(!entry_nodes(&bad, size, MPIDR, FREQUENCY));
    }
    for (size_t i = 0; i < sizeof(span_mutation) / sizeof(span_mutation[0]); ++i) {
        bad = good;
        n306_put64(bad.view.adt + OFF_DRAM, span_mutation[i].base);
        n306_put64(bad.view.adt + OFF_DRAM + N309_DRAM_NAME_STRIDE, span_mutation[i].span);
        CHECK(!entry_nodes(&bad, size, MPIDR, FREQUENCY));
    }
    for (size_t i = 0; i < sizeof(bad_offset) / sizeof(bad_offset[0]); ++i) {
        bad = good;
        bad.view.meta.dram_base_offset = bad_offset[i];
        CHECK(!entry_nodes(&bad, size, MPIDR, FREQUENCY));
    }
    for (size_t i = 0; i < sizeof(defaults_mutation) / sizeof(defaults_mutation[0]); ++i) {
        bad = good;
        n306_put32(bad.view.adt + defaults_mutation[i].offset, defaults_mutation[i].value);
        CHECK(!entry_nodes(&bad, size, MPIDR, FREQUENCY));
    }
    for (size_t i = 0; i < sizeof(bad_defaults_offset) / sizeof(bad_defaults_offset[0]); ++i) {
        bad = good;
        bad.view.meta.defaults_offset = bad_defaults_offset[i];
        CHECK(!entry_nodes(&bad, size, MPIDR, FREQUENCY));
    }
    bad = good;
    bad.view.meta.bootargs_map_offset = OFF_BOOTARGS + 2;                       /* misaligned map offset */
    CHECK(!entry_nodes(&bad, size, MPIDR, FREQUENCY));
    bad = good;
    bad.view.meta.devtree_map_offset = size - 8;                                /* map offset past end */
    CHECK(!entry_nodes(&bad, size, MPIDR, FREQUENCY));
    bad = good;
    n306_put32(bad.view.adt + OFF_DEVTREE + 16 + 4, 7);                         /* cpus nChildren 7: walker end */
    CHECK(entry_nodes(&bad, size, MPIDR, FREQUENCY) != ADT_NODES);
    CHECK(!entry_nodes(&good, size, MPIDR + 1, FREQUENCY));                     /* MPIDR mismatch */
    CHECK(!entry_nodes(&good, size, MPIDR, FREQUENCY + 1));                     /* CNTFRQ mismatch */
    bad = good;
    bad.view.adt[OFF_CPU0 + 216 + 176 + 8 + 36 + 3] = '1';                      /* cpu2 renamed "cpu1" */
    CHECK(n10_rt_validate_adt(bad.view.adt, size) != N10_RT_OK);
    CHECK(entry_nodes(&bad, size, MPIDR, FREQUENCY) == ADT_NODES);              /* structural walk alone allows it */

    CHECK(!generate(scratch, regs, N307_CPUS + 1, DRAM_BASE, DRAM_SIZE, &other));
    memcpy(wide, regs, sizeof(wide));
    wide[5] = 0x100000000ULL;
    CHECK(!generate(scratch, wide, N307_CPUS, DRAM_BASE, DRAM_SIZE, &other));
    for (size_t i = 0; i < sizeof(generator_reject) / sizeof(generator_reject[0]); ++i)
        CHECK(!generate(scratch, regs, N307_CPUS, generator_reject[i].base, generator_reject[i].span, &other));
    CHECK(generate(scratch, regs, N307_CPUS, DRAM_BASE, BASE + N304_ARENA_BYTES - DRAM_BASE, &other) == ADT_BYTES &&
          n304_fnv(scratch, ADT_BYTES) != ADT_FNV);                            /* arena ends at DRAM end; d moves */

    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    expected.args_hash = ARGS_FNV;
    expected.adt_hash = ADT_FNV;
    expected.adt_nodes = ADT_NODES;
    make_record(record, ARGS_FNV, ADT_FNV, ADT_NODES, DRAM_SIZE);
    CHECK(n306_host_record_valid(record, sizeof(record), &expected));
    memcpy(altered, record, sizeof(record));
    altered[2] = '0';
    altered[3] = '9';                                                          /* N309 tag */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, ARGS_FNV, ADT_FNV, ADT_NODES, DRAM_SIZE + 0x4000);    /* r[3] off by 0x4000 */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, ARGS_FNV, ADT_FNV, ADT_NODES - 1, DRAM_SIZE);         /* n=0c */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, ARGS_FNV, ADT_FNV ^ 1, ADT_NODES, DRAM_SIZE);
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, ARGS_FNV ^ 1, ADT_FNV, ADT_NODES, DRAM_SIZE);
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    memcpy(altered, record, sizeof(record));
    altered[N304_HOST_COMMIT_OFFSET] = N304_HOST_PENDING;
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    if (checks != EXPECTED_CHECKS) {
        fprintf(stderr, "v310 fixture check count %d\n", checks);
        return 1;
    }
    puts("v310 adt fixture PASS");
    return 0;
}
