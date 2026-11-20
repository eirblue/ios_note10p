/* SPDX-License-Identifier: GPL-2.0-only */
/* v305 host fixture: boot_args with CommandLine, synthetic ADT, and a C mirror of the stub field checks. */
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "v305_abi_contract.h"

#define BASE 0x90000000ULL /* synthetic 16 KiB-aligned base */
#define ADT_BYTES 112U
#define EXPECTED_CHECKS 20

_Static_assert(offsetof(struct n10_rt_boot_layout, virtBase) == N305_VIRT, "virtBase");
_Static_assert(offsetof(struct n10_rt_boot_layout, physBase) == N305_PHYS, "physBase");
_Static_assert(offsetof(struct n10_rt_boot_layout, memSize) == N305_MEMSIZE, "memSize");
_Static_assert(offsetof(struct n10_rt_boot_layout, topOfKernelData) == N305_TOP, "topOfKernelData");
_Static_assert(offsetof(struct n10_rt_boot_layout, machineType) == N305_MACHINE, "machineType");
_Static_assert(offsetof(struct n10_rt_boot_layout, deviceTreeP) == 96, "deviceTreeP");
_Static_assert(offsetof(struct n10_rt_boot_layout, deviceTreeLength) == 104, "deviceTreeLength");
_Static_assert(offsetof(struct n10_rt_boot_layout, CommandLine) == N305_CMDLINE, "CommandLine");
_Static_assert(sizeof(((struct n10_rt_boot_layout *)0)->CommandLine) == N305_CMDLINE_BYTES, "CommandLine bytes");
_Static_assert(offsetof(struct n10_rt_boot_layout, bootFlags) == N305_BOOTFLAGS, "bootFlags");
_Static_assert(offsetof(struct n10_rt_boot_layout, memSizeActual) == N305_MEMACTUAL, "memSizeActual");
_Static_assert(sizeof(N305_COMMAND) - 1 == N305_COMMAND_BYTES, "command length");

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v305 fixture failed at line %d\n", __LINE__); \
            return 1;                                                     \
        }                                                                 \
        ++checks;                                                         \
    } while (0)

static uint64_t get64(const uint8_t *p)
{
    uint64_t value = 0;
    for (int i = 7; i >= 0; --i)
        value = (value << 8) | p[i];
    return value;
}

static uint32_t get32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static void put64(uint8_t *p, uint64_t value)
{
    for (int i = 0; i < 8; ++i)
        p[i] = (uint8_t)(value >> (8 * i));
}

/* Mirror of the v305 stub predicate added after the deviceTreeLength check. */
static int stub_fields_ok(const uint8_t *a, uint64_t base)
{
    const uint8_t *line = a + N305_CMDLINE;

    if (get64(a + N305_VIRT) != base || get64(a + N305_PHYS) != base ||
        get64(a + N305_MEMSIZE) != N304_ARENA_BYTES ||
        get64(a + N305_TOP) - base != get64(a + N305_MEMSIZE) ||
        get32(a + N305_MACHINE) || get64(a + N305_BOOTFLAGS) ||
        get64(a + N305_MEMACTUAL) < N304_ARENA_BYTES || !line[0])
        return 0;
    for (uint32_t i = 0; i < N305_CMDLINE_BYTES; ++i) {
        if (!line[i])
            return 1;
        if ((uint32_t)line[i] - 32U > 94U)
            return 0;
    }
    return 0;
}

int main(void)
{
    static const char compatible[] = "n10,fixture"; /* synthetic root compatible */
    uint8_t good[N304_ARGS_BYTES], empty[N304_ARGS_BYTES], bad[N304_ARGS_BYTES], adt[N304_ADT_STORAGE];
    const struct n10_rt_boot_fields v304_fields = {
        .virtual_base = BASE, .physical_base = BASE, .memory_size = N304_ARENA_BYTES,
        .top_of_kernel = BASE + N304_ARENA_BYTES, .device_tree_pointer = BASE + N304_ADT_OFFSET,
        .device_tree_length = ADT_BYTES, .memory_size_actual = N304_ARENA_BYTES,
    };
    const struct {
        size_t offset;
        uint64_t value;
        int wide;
    } mutation[] = {
        {N305_VIRT, BASE + N304_ARENA_BYTES, 1},
        {N305_PHYS, BASE + N304_ARENA_BYTES, 1},
        {N305_MEMSIZE, 2 * N304_ARENA_BYTES, 1},
        {N305_TOP, BASE + 2 * N304_ARENA_BYTES, 1},
        {N305_MACHINE, 1, 0},
        {N305_BOOTFLAGS, 1, 1},
        {N305_MEMACTUAL, N304_ARENA_BYTES - 1, 1},
        {N305_CMDLINE, 0, 2},
        {N305_CMDLINE + 3, 0x1f, 2},
        {N305_CMDLINE + 3, 0x7f, 2},
    };

    CHECK(n304_arguments(BASE, ADT_BYTES, good) == N10_RT_OK);
    CHECK(n304_fnv(good, N304_ARGS_BYTES) == 0xb9e21545U);
    CHECK(!memcmp(good + N305_CMDLINE, N305_COMMAND, N305_COMMAND_BYTES) &&
          good[N305_CMDLINE + N305_COMMAND_BYTES] == 0);
    CHECK(n10_rt_serialize_boot_args(&v304_fields, empty, sizeof(empty)) == N10_RT_OK);
    CHECK(n304_fnv(empty, N304_ARGS_BYTES) == 0xb13ee059U);
    CHECK(n304_adt(adt, compatible, sizeof(compatible)) == ADT_BYTES);
    CHECK(n304_fnv(adt, ADT_BYTES) == 0xe6245a57U);
    CHECK(n10_rt_validate_adt(adt, ADT_BYTES) == N10_RT_OK);
    CHECK(stub_fields_ok(good, BASE));
    for (size_t i = 0; i < sizeof(mutation) / sizeof(mutation[0]); ++i) {
        memcpy(bad, good, sizeof(bad));
        if (mutation[i].wide == 1)
            put64(bad + mutation[i].offset, mutation[i].value);
        else
            bad[mutation[i].offset] = (uint8_t)mutation[i].value;
        CHECK(!stub_fields_ok(bad, BASE));
    }
    memcpy(bad, good, sizeof(bad));
    memset(bad + N305_CMDLINE, 'a', N305_CMDLINE_BYTES);
    CHECK(!stub_fields_ok(bad, BASE));
    if (checks != EXPECTED_CHECKS) {
        fprintf(stderr, "v305 fixture check count %d\n", checks);
        return 1;
    }
    puts("v305 boot_args fixture PASS");
    return 0;
}
