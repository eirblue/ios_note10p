/* SPDX-License-Identifier: GPL-2.0-only */
/* v339 host fixture (new cases only): the N339PS20 kernel and host record format tags with the unchanged 250-byte record,
 * the N339PS2T validator with the unchanged N315 crumbs (an N338PS2T record is rejected), and the v339 contract: n310_adt
 * with the memory-map RAMDisk property (nProps 4, size 2644 + align4(compatible)) accepted by n10_rt_validate_adt and the
 * boot_args CommandLine with rd=md0. Synthetic values only: synthetic window base, image size, DRAM span, cpu regs and
 * record fields; no real kernel bytes, entry, address or register. */
#include <stdio.h>
#include "v339_abi_contract.h"
#include "v339_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 32 MiB-aligned window base >= 2 GiB */
#define MPIDR 0x81000010ULL          /* synthetic raw MPIDR: affinity 0x10 */
#define ADT_NODES 14U
#define ADT_FNV 0xc1cb3618U          /* synthetic record field */
#define ARGS_FNV 0xaee810a3U         /* synthetic record field */
#define IMAGE_FNV 0x4e154d31U        /* synthetic image word-FNV (record field) */
#define IMAGE_TICKS 0x1234U          /* synthetic MMU-off hash ticks */
#define ENTRY 0x4010U                /* synthetic entry offset */
#define ENTRY_WORD 0x14000001U       /* synthetic 'b .+4' at the entry */
#define FIXTURE_GROUPS 3
#define FIXTURE_VARIANTS 6
#define EXPECTED_CHECKS 6
#define SYN_IMAGE_BYTES 0x100000U    /* synthetic loaded-image size (16 KiB multiple) */
#define SYN_FREQUENCY 26000000U      /* synthetic cpu0 timebase frequency */
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v339 fixture failed at line %d\n", __LINE__); \
            return 1;                                                     \
        }                                                                 \
        ++checks;                                                         \
    } while (0)

static void put_hex(char *field, size_t digits, uint64_t value)
{
    static const char hex[] = "0123456789abcdef";

    while (digits) {
        field[--digits] = hex[value & 15];
        value >>= 4;
    }
}

static uint64_t get64(const uint8_t *in)
{
    uint64_t value = 0;

    for (int i = 7; i >= 0; --i)
        value = value << 8 | in[i];
    return value;
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
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10, .args_hash = ARGS_FNV,
                                                 .adt_hash = ADT_FNV, .adt_nodes = ADT_NODES, .image_hash = IMAGE_FNV,
                                                 .entry_offset = ENTRY, .entry_word = ENTRY_WORD};
    int code = -2;
    static uint8_t adt[N307_ADT_STORAGE], args[N304_ARGS_BYTES];
    static const char compatible[] = "synthetic,note10-test";
    static const uint64_t regs[N307_CPUS] = {0, 1, 2, 3, 0x100, 0x101, 0x200, 0x201};
    const uint64_t handoff = BASE + N311_KERNEL_OFFSET + SYN_IMAGE_BYTES;
    struct n310_offsets offsets;
    uint32_t size, map, ramdisk;

    /* Group 1: kernel and host record format tags N339PS20; the record length stays 250. */
    CHECK(snprintf(text, sizeof(text), N304_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_RECORD_BYTES &&
          N304_RECORD_BYTES == 250 && !memcmp(text, "N339PS20", 8));
    CHECK(snprintf(host, sizeof(host), N304_HOST_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_HOST_RECORD_BYTES &&
          N304_HOST_RECORD_BYTES == 250 && !memcmp(host, "N339PS20", 8) && !memcmp(text, host, sizeof(host)));

    /* Group 2: N339PS2T validator with the unchanged N315 crumbs; an N338PS2T record is not a v339 witness. */
    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    make_record(record, "N339PS2");
    CHECK(n306_host_record_valid(record, sizeof(record), &expected) &&
          n315_crumb_trace(crumbs, sizeof(crumbs) - 1, &code) == 7 && code == 0);
    make_record(altered, "N338PS2");
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));

    /* Group 3: v339 contract. memory-map{name, BootArgs, DeviceTree, RAMDisk} with RAMDisk = {H + 0x2000, 0x2000} right
     * after DeviceTree; the ADT size is 2644 + align4(compatible) and the walk validator accepts it; the boot_args
     * CommandLine is "-v n10diag=305 rd=md0" (21 bytes, NUL-terminated). */
    size = n310_adt(adt, compatible, sizeof(compatible), handoff, regs, N307_CPUS, SYN_FREQUENCY,
                    0x80000000ULL, 0x400000000ULL, &offsets);
    map = offsets.bootargs - 36 - 48 - 8; /* memory-map node header: before its 48-byte name property */
    ramdisk = offsets.devtree + 16;       /* RAMDisk property right after the DeviceTree value */
    CHECK(size == 2644 + ((sizeof(compatible) + 3) & ~3U) && n10_rt_validate_adt(adt, size) == N10_RT_OK &&
          get64(adt + map) == 4 && !memcmp(adt + map + 8, "name", 5) && !memcmp(adt + map + 44, "memory-map", 11) &&
          get64(adt + offsets.devtree) == handoff + N306_ADT_OFFSET && get64(adt + offsets.devtree + 8) == size &&
          !memcmp(adt + ramdisk, "RAMDisk\0", 8) && adt[ramdisk + 32] == 16 && !adt[ramdisk + 33] &&
          get64(adt + ramdisk + 36) == handoff + N339_RAMDISK_OFFSET &&
          get64(adt + ramdisk + 44) == N339_RAMDISK_BYTES && get64(adt + ramdisk + 52) == 7);
    CHECK(n311_arguments(BASE, size, SYN_IMAGE_BYTES, args) == N10_RT_OK && N305_COMMAND_BYTES == 21 &&
          !memcmp(args + N305_CMDLINE, "-v n10diag=305 rd=md0", N305_COMMAND_BYTES + 1) &&
          get64(args + N305_TOP) == handoff + N316_HANDOFF_BYTES);

    if (checks != EXPECTED_CHECKS || FIXTURE_VARIANTS != EXPECTED_CHECKS || FIXTURE_GROUPS != 3) {
        fprintf(stderr, "v339 fixture check count %d\n", checks);
        return 1;
    }
    puts("v339 tag fixture PASS");
    return 0;
}
