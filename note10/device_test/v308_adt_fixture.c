/* SPDX-License-Identifier: GPL-2.0-only */
/* v308 host fixture (v307 entry predicates carried forward, N308PS2T record): eight-CPU, memory-map ADT, boot_args at the ADT offset, a C mirror of the stub
 * walker/memory-map/cpu0 predicate, and the N308PS2T record validator. Synthetic values only. */
#include <stdio.h>
#include "v308_abi_contract.h"
#include "v308_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 16 KiB-aligned base */
#define COMPATIBLE "n10,fixture"     /* synthetic root compatible */
#define MPIDR 0x81000010ULL          /* synthetic raw MPIDR: affinity 0x10 */
#define FREQUENCY 19200000U          /* synthetic CNTFRQ */
#define MMFR0 0x0000000000101122ULL  /* synthetic observational value */
#define ADT_BYTES 1816U
#define ADT_NODES 12U
#define ADT_FNV 0x9bd6a46fU
#define ARGS_FNV 0xfdae664cU
#define OFF_BOOTARGS 248U
#define OFF_DEVTREE 300U
#define OFF_REG 496U
#define OFF_TBF 536U
#define EXPECTED_CHECKS 27
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

_Static_assert(offsetof(struct n304_metadata, cpu_reg_offset) == N306_META_REG_OFF, "reg offset slot");
_Static_assert(offsetof(struct n304_metadata, timebase_offset) == N306_META_TBF_OFF, "tbf offset slot");
_Static_assert(offsetof(struct n304_metadata, bootargs_map_offset) == N307_META_BOOTARGS_OFF, "BootArgs slot");
_Static_assert(offsetof(struct n304_metadata, devtree_map_offset) == N307_META_DEVTREE_OFF, "DeviceTree slot");
_Static_assert(offsetof(union n304_storage, view.meta) == N304_META_OFFSET, "meta offset");
_Static_assert(offsetof(union n304_storage, view.adt) == N306_ADT_OFFSET, "adt offset");
_Static_assert(N306_ADT_OFFSET + N307_ADT_STORAGE <= N304_ARENA_BYTES, "adt inside arena");
_Static_assert(sizeof(union n304_storage) == N304_ARENA_BYTES, "arena size");

static const uint64_t regs[N307_CPUS] = {0x10, 0x11, 0x12, 0x13, 0x110, 0x111, 0x210, 0x211};
static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v308 fixture failed at line %d\n", __LINE__); \
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

/* Mirror of the v306/v307 stub ADT predicates; returns the walked node count, or 0 on park. */
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
        !map_ok(adt, size, meta->devtree_map_offset, "DeviceTr", BASE + N306_ADT_OFFSET, size))
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

static void make_record(char *record, uint32_t args, uint32_t adt, uint32_t nodes)
{
    char text[N304_HOST_RECORD_BYTES + 1];

    snprintf(text, sizeof(text), N304_HOST_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID);
    memcpy(record, text, N304_HOST_RECORD_BYTES);
    put_hex(record + N304_HOST_REG_OFFSET, 16, BASE);
    put_hex(record + N304_HOST_REG_OFFSET + N304_HOST_REG_STRIDE, 16, MPIDR);
    put_hex(record + N304_HOST_REG_OFFSET + 2 * N304_HOST_REG_STRIDE, 16, MMFR0);
    put_hex(record + N304_HOST_ARGS_HASH_OFFSET, 8, args);
    put_hex(record + N304_HOST_ADT_HASH_OFFSET, 8, adt);
    put_hex(record + N304_HOST_ADT_LENGTH_OFFSET, 2, nodes);
    put_hex(record + N304_HOST_SCTLR_OFFSET, 16, 0x30d00800);
    record[N304_HOST_EL_OFFSET] = '1';
    record[N304_HOST_DAIF_OFFSET] = 'f';
    record[N304_HOST_COMMIT_OFFSET] = N304_HOST_COMMITTED;
    put_hex(record + N304_HOST_CSUM_OFFSET, 8, n306_host_body_checksum(record));
}

int main(void)
{
    static union n304_storage good, bad;
    static uint8_t scratch[N307_ADT_STORAGE];
    struct n307_offsets offsets;
    uint64_t wide[N307_CPUS];
    uint32_t size;
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10};
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
    };

    size = n307_adt(good.view.adt, COMPATIBLE, sizeof(COMPATIBLE), BASE, regs, N307_CPUS, FREQUENCY, &offsets);
    CHECK(size == ADT_BYTES && offsets.bootargs == OFF_BOOTARGS && offsets.devtree == OFF_DEVTREE &&
          offsets.reg == OFF_REG && offsets.timebase == OFF_TBF);
    CHECK(n304_fnv(good.view.adt, size) == ADT_FNV);
    CHECK(n10_rt_validate_adt(good.view.adt, size) == N10_RT_OK);
    CHECK(n304_arguments(BASE, size, good.view.args) == N10_RT_OK);
    CHECK(n304_fnv(good.view.args, N304_ARGS_BYTES) == ARGS_FNV);
    good.view.meta.cpu_reg_offset = offsets.reg;
    good.view.meta.timebase_offset = offsets.timebase;
    good.view.meta.bootargs_map_offset = offsets.bootargs;
    good.view.meta.devtree_map_offset = offsets.devtree;
    CHECK(entry_nodes(&good, size, MPIDR, FREQUENCY) == ADT_NODES);

    for (size_t i = 0; i < sizeof(word_mutation) / sizeof(word_mutation[0]); ++i) {
        bad = good;
        n306_put32(bad.view.adt + word_mutation[i].offset, word_mutation[i].value);
        CHECK(!entry_nodes(&bad, size, MPIDR, FREQUENCY));
    }
    bad = good;
    bad.view.meta.bootargs_map_offset = OFF_BOOTARGS + 2;                       /* misaligned map offset */
    CHECK(!entry_nodes(&bad, size, MPIDR, FREQUENCY));
    bad = good;
    bad.view.meta.devtree_map_offset = size - 8;                                /* map offset past end */
    CHECK(!entry_nodes(&bad, size, MPIDR, FREQUENCY));
    bad = good;
    n306_put32(bad.view.adt + 320, 7);                                         /* cpus nChildren 7: walker end */
    CHECK(entry_nodes(&bad, size, MPIDR, FREQUENCY) != ADT_NODES);
    CHECK(!entry_nodes(&good, size, MPIDR + 1, FREQUENCY));                     /* MPIDR mismatch */
    CHECK(!entry_nodes(&good, size, MPIDR, FREQUENCY + 1));                     /* CNTFRQ mismatch */
    CHECK(!n307_adt(scratch, COMPATIBLE, sizeof(COMPATIBLE), BASE, regs, N307_CPUS + 1, FREQUENCY, &offsets));
    memcpy(wide, regs, sizeof(wide));
    wide[5] = 0x100000000ULL;
    CHECK(!n307_adt(scratch, COMPATIBLE, sizeof(COMPATIBLE), BASE, wide, N307_CPUS, FREQUENCY, &offsets));
    bad = good;
    bad.view.adt[368 + 216 + 176 + 8 + 36 + 3] = '1';                          /* cpu2 renamed "cpu1" */
    CHECK(n10_rt_validate_adt(bad.view.adt, size) != N10_RT_OK);
    CHECK(entry_nodes(&bad, size, MPIDR, FREQUENCY) == ADT_NODES);              /* structural walk alone allows it */

    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    expected.args_hash = ARGS_FNV;
    expected.adt_hash = ADT_FNV;
    expected.adt_nodes = ADT_NODES;
    make_record(record, ARGS_FNV, ADT_FNV, ADT_NODES);
    CHECK(n306_host_record_valid(record, sizeof(record), &expected));
    memcpy(altered, record, sizeof(record));
    altered[3] = '7';                                                          /* N307 tag */
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, ARGS_FNV, ADT_FNV, ADT_NODES + 1);
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, ARGS_FNV, ADT_FNV ^ 1, ADT_NODES);
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    make_record(altered, ARGS_FNV ^ 1, ADT_FNV, ADT_NODES);
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    memcpy(altered, record, sizeof(record));
    altered[N304_HOST_COMMIT_OFFSET] = N304_HOST_PENDING;
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));
    if (checks != EXPECTED_CHECKS) {
        fprintf(stderr, "v308 fixture check count %d\n", checks);
        return 1;
    }
    puts("v308 adt fixture PASS");
    return 0;
}
