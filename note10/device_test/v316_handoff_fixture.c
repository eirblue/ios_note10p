/* SPDX-License-Identifier: GPL-2.0-only */
/* v316 host fixture (new cases only): the N316PS20 record tag and the N316_HANDOFF_BYTES constants, n311_arguments for the
 * handoff layout (topOfKernelData = H + 16 KiB, deviceTreeP = KVA of H + N306_ADT_OFFSET), the image bound, XNU's linear
 * KVA relation, n310_adt with base H, a C mirror of the Linux copy into H and the enter hash refusal, a C mirror of the stub's
 * retargeted deviceTreeP/topOfKernel/BootArgs/DeviceTree compares, a C mirror of the stub's handoff compare loop and the
 * N316PS2T validator with the unchanged N315 crumbs. Synthetic values only: synthetic window base, image size, compatible,
 * cpu regs, frequency, DRAM span and record fields; no real kernel bytes, entry, address or register. */
#include <stdio.h>
#include "v316_abi_contract.h"
#include "v316_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 32 MiB-aligned window base >= 2 GiB */
#define DRAM_BASE 0x80000000ULL      /* synthetic DRAM span containing the window */
#define DRAM_SIZE 0x40000000ULL
#define MPIDR 0x81000010ULL          /* synthetic raw MPIDR: affinity 0x10 */
#define FREQUENCY 26000000U          /* synthetic timebase */
#define ADT_NODES 13U
#define ADT_FNV 0xc1cb3618U          /* synthetic record field */
#define ARGS_FNV 0xaee810a3U         /* synthetic record field */
#define IMAGE_FNV 0x4e154d31U        /* v312 synthetic image word-FNV (record field) */
#define IMAGE_TICKS 0x1234U          /* synthetic MMU-off hash ticks */
#define ENTRY 0x4010U                /* v312 synthetic entry offset */
#define ENTRY_WORD 0x14000001U       /* v312 synthetic 'b .+4' at the entry */
#define IMAGE_BYTES 0x1240000U       /* synthetic loaded-image size (16 KiB multiple) */
#define COMPAT "synthetic,note10"
#define FIXTURE_GROUPS 9
#define FIXTURE_VARIANTS 29
#define EXPECTED_CHECKS 29
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

_Static_assert(N316_HANDOFF_BYTES == 0x4000 && N316_HANDOFF_BYTES == N304_ARENA_BYTES, "handoff page is one arena page");
_Static_assert(N306_ADT_OFFSET + N307_ADT_STORAGE <= N316_HANDOFF_BYTES, "ADT copy fits the handoff page");
_Static_assert(N306_ADT_OFFSET == 2048 && N304_ARGS_BYTES == 1152, "copy offsets");
_Static_assert(N304_ARGS_BYTES % 4 == 0 && N306_ADT_OFFSET % 4 == 0, "aligned 32-bit compare ranges");

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v316 fixture failed at line %d\n", __LINE__); \
            return 1;                                                     \
        }                                                                 \
        ++checks;                                                         \
    } while (0)

static uint8_t arena_args[N304_ARGS_BYTES], arena_adt[N307_ADT_STORAGE], page[N316_HANDOFF_BYTES], spare[N316_HANDOFF_BYTES];

/* Mirror of the v316 prepare copy: zero the page, args at +0, ADT at +N306_ADT_OFFSET. */
static void copy_to_handoff(uint8_t *out, uint32_t adt_bytes)
{
    memset(out, 0, N316_HANDOFF_BYTES);
    memcpy(out, arena_args, N304_ARGS_BYTES);
    memcpy(out + N306_ADT_OFFSET, arena_adt, adt_bytes);
}

/* Mirror of the v316 enter refusal on the copy: both FNVs equal the arena hashes. */
static int copy_hash_ok(const uint8_t *copy, uint32_t adt_bytes, uint32_t args_hash, uint32_t adt_hash)
{
    return n304_fnv(copy, N304_ARGS_BYTES) == args_hash && n304_fnv(copy + N306_ADT_OFFSET, adt_bytes) == adt_hash;
}

/* Mirror of the v316 stub retargeted compares (1 = accepted, 0 = park): x1 = kernel offset + image_bytes, H = B + x1,
 * deviceTreeP == virtBase + x1 + ADT offset, x1 + handoff <= memSize, topOfKernelData == B + x1 + handoff,
 * memory-map BootArgs == (H, 1152) and DeviceTree == (H + ADT offset, adt_bytes). */
static int stub_retargeted_ok(const uint8_t *args, const uint8_t *adt, uint64_t base, uint64_t image_bytes,
                              uint32_t adt_bytes, const struct n310_offsets *offsets)
{
    uint64_t x1 = N311_KERNEL_OFFSET + image_bytes, h = base + x1;

    return n312_le64(args + 96) == N311_VIRT_BASE + x1 + N306_ADT_OFFSET &&
           x1 + N316_HANDOFF_BYTES <= N315_BOOT_MEMSIZE && n312_le64(args + N305_MEMSIZE) == N315_BOOT_MEMSIZE &&
           n312_le64(args + N305_TOP) == base + x1 + N316_HANDOFF_BYTES &&
           n312_le64(adt + offsets->bootargs) == h && n312_le64(adt + offsets->bootargs + 8) == N304_ARGS_BYTES &&
           n312_le64(adt + offsets->devtree) == h + N306_ADT_OFFSET && n312_le64(adt + offsets->devtree + 8) == adt_bytes;
}

/* Mirror of the v316 stub handoff compare: 32-bit words over [0, 1152), then [2048, 2048 + adt_bytes); 1 = pass, 0 = park.
 * arena and copy are both laid out as a 16 KiB page (args at 0, ADT at 2048). */
static int stub_handoff_ok(const uint8_t *arena, const uint8_t *copy, uint32_t adt_bytes)
{
    uint64_t x7 = 0, x8 = N304_ARGS_BYTES;

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
    uint8_t args[N304_ARGS_BYTES], mutated[N304_ARGS_BYTES], adt_mutated[N307_ADT_STORAGE];
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10, .args_hash = ARGS_FNV,
                                                 .adt_hash = ADT_FNV, .adt_nodes = ADT_NODES, .image_hash = IMAGE_FNV,
                                                 .entry_offset = ENTRY, .entry_word = ENTRY_WORD};
    struct n310_offsets offsets;
    uint32_t adt_bytes, args_hash, adt_hash;
    int code = -2;

    /* Group 1: kernel record format tag N316PS20 (static handoff constants above). */
    CHECK(snprintf(text, sizeof(text), N304_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_RECORD_BYTES &&
          !memcmp(text, "N316PS20", 8));

    /* Group 5 input: n310_adt with base H (memory-map values), synthetic compatible/regs/frequency/DRAM span. */
    adt_bytes = n310_adt(arena_adt, COMPAT, sizeof(COMPAT), h, regs, N307_CPUS, FREQUENCY, DRAM_BASE, DRAM_SIZE, &offsets);

    /* Group 2: n311_arguments on the handoff layout. */
    CHECK(adt_bytes && n311_arguments(BASE, adt_bytes, IMAGE_BYTES, args) == N10_RT_OK);
    CHECK(n312_le64(args + N305_PHYS) == BASE && n312_le64(args + N305_VIRT) == N311_VIRT_BASE &&
          n312_le64(args + N305_MEMSIZE) == 0x3004000ULL);
    CHECK(n312_le64(args + N305_TOP) == BASE + 0x1004000ULL + IMAGE_BYTES + 0x4000ULL);
    CHECK(n312_le64(args + 96) == N311_VIRT_BASE + 0x1004000ULL + IMAGE_BYTES + 2048 && n312_le32(args + 104) == adt_bytes);
    CHECK(n312_le64(args + N305_MEMACTUAL) == 0x10000000ULL);

    /* Group 3: image bound memSize - kernel offset - handoff page. */
    CHECK(n311_image_bytes_ok(0x1ffc000) && n311_arguments(BASE, adt_bytes, 0x1ffc000, mutated) == N10_RT_OK);
    CHECK(!n311_image_bytes_ok(0x2000000) && n311_arguments(BASE, adt_bytes, 0x2000000, mutated) == N10_RT_INVALID);

    /* Group 4: XNU's linear KVA relation and containment. */
    CHECK(n312_le64(args + 96) - n312_le64(args + N305_VIRT) == (h + N306_ADT_OFFSET) - n312_le64(args + N305_PHYS));
    CHECK(n312_le64(args + 96) + adt_bytes <= n312_le64(args + N305_VIRT) + n312_le64(args + N305_MEMSIZE));
    CHECK(h + N316_HANDOFF_BYTES <= BASE + n312_le64(args + N305_MEMSIZE));

    /* Group 5: memory-map BootArgs = (H, 1152), DeviceTree = (H + 2048, size); size unchanged. */
    CHECK(adt_bytes == 1948 + ((sizeof(COMPAT) + 3) & ~3U));
    CHECK(n312_le64(arena_adt + offsets.bootargs) == h && n312_le64(arena_adt + offsets.bootargs + 8) == N304_ARGS_BYTES);
    CHECK(n312_le64(arena_adt + offsets.devtree) == h + N306_ADT_OFFSET &&
          n312_le64(arena_adt + offsets.devtree + 8) == adt_bytes);

    /* Group 6: Linux copy mirror and enter refusal. */
    memcpy(arena_args, args, sizeof(args));
    args_hash = n304_fnv(arena_args, N304_ARGS_BYTES);
    adt_hash = n304_fnv(arena_adt, adt_bytes);
    memset(page, 0xa5, sizeof(page));
    copy_to_handoff(page, adt_bytes);
    memset(spare, 0, sizeof(spare));
    memcpy(spare, arena_args, N304_ARGS_BYTES);
    memcpy(spare + N306_ADT_OFFSET, arena_adt, adt_bytes);
    CHECK(!memcmp(page, spare, sizeof(page)));
    CHECK(copy_hash_ok(page, adt_bytes, args_hash, adt_hash));
    page[N306_ADT_OFFSET + 40] ^= 1;
    CHECK(!copy_hash_ok(page, adt_bytes, args_hash, adt_hash));
    page[N306_ADT_OFFSET + 40] ^= 1;

    /* Group 7: stub retargeted compares; the v315 B-based values each park. */
    CHECK(stub_retargeted_ok(args, arena_adt, BASE, IMAGE_BYTES, adt_bytes, &offsets));
    memcpy(mutated, args, sizeof(args));
    n306_put64(mutated + 96, N311_VIRT_BASE + N306_ADT_OFFSET);
    CHECK(!stub_retargeted_ok(mutated, arena_adt, BASE, IMAGE_BYTES, adt_bytes, &offsets));
    memcpy(mutated, args, sizeof(args));
    n306_put64(mutated + N305_TOP, BASE + N311_KERNEL_OFFSET + IMAGE_BYTES);
    CHECK(!stub_retargeted_ok(mutated, arena_adt, BASE, IMAGE_BYTES, adt_bytes, &offsets));
    memcpy(adt_mutated, arena_adt, sizeof(adt_mutated));
    n306_put64(adt_mutated + offsets.bootargs, BASE);
    CHECK(!stub_retargeted_ok(args, adt_mutated, BASE, IMAGE_BYTES, adt_bytes, &offsets));
    memcpy(adt_mutated, arena_adt, sizeof(adt_mutated));
    n306_put64(adt_mutated + offsets.devtree, BASE + N306_ADT_OFFSET);
    CHECK(!stub_retargeted_ok(args, adt_mutated, BASE, IMAGE_BYTES, adt_bytes, &offsets));

    /* Group 8: stub handoff compare over [0, 1152) and [2048, 2048 + adt_bytes); spare = arena page layout. */
    memset(spare + N304_ARGS_BYTES, 0x5a, N306_ADT_OFFSET - N304_ARGS_BYTES); /* arena meta region differs from the copy */
    CHECK(stub_handoff_ok(spare, page, adt_bytes));
    page[100] ^= 1;
    CHECK(!stub_handoff_ok(spare, page, adt_bytes));
    page[100] ^= 1;
    page[N306_ADT_OFFSET + 500] ^= 1;
    CHECK(!stub_handoff_ok(spare, page, adt_bytes));
    page[N306_ADT_OFFSET + 500] ^= 1;
    page[N306_ADT_OFFSET + adt_bytes - 1] ^= 1;
    CHECK(!stub_handoff_ok(spare, page, adt_bytes));
    page[N306_ADT_OFFSET + adt_bytes - 1] ^= 1;
    page[N304_ARGS_BYTES + 16] ^= 1;
    CHECK(stub_handoff_ok(spare, page, adt_bytes));
    page[N304_ARGS_BYTES + 16] ^= 1;

    /* Group 9: N316PS2T validator with the unchanged N315 crumbs; an N315PS2T record is not a v316 witness. */
    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    make_record(record, "N316PS2");
    CHECK(n306_host_record_valid(record, sizeof(record), &expected) &&
          n315_crumb_trace(crumbs, sizeof(crumbs) - 1, &code) == 7 && code == 0);
    make_record(altered, "N315PS2");
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));

    if (checks != EXPECTED_CHECKS || FIXTURE_VARIANTS != EXPECTED_CHECKS) {
        fprintf(stderr, "v316 fixture check count %d\n", checks);
        return 1;
    }
    puts("v316 handoff fixture PASS");
    return 0;
}
