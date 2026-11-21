/* SPDX-License-Identifier: GPL-2.0-only */
/* v319 host fixture (new cases only): the slid XNU VM layout constants (virtBase 0xfffffe0006000000, link base
 * 0xfffffe0007004000, builder VA rule), n311_arguments with the new virtBase, n312_entry_offset on a synthetic Mach-O slid
 * to the new link base, and the N319PS2T validator (an N318PS2T record is rejected). Synthetic values only: synthetic
 * window base, image and record fields; no real kernel bytes, entry, address or register. */
#include <stdio.h>
#include "v319_abi_contract.h"
#include "v319_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 32 MiB-aligned window base >= 2 GiB */
#define MPIDR 0x81000010ULL          /* synthetic raw MPIDR: affinity 0x10 */
#define ADT_BYTES 2256U              /* synthetic ADT length */
#define ADT_NODES 13U
#define ADT_FNV 0xc1cb3618U          /* synthetic record field */
#define ARGS_FNV 0xaee810a3U         /* synthetic record field */
#define IMAGE_BYTES 32768U           /* synthetic image size (16 KiB multiple) */
#define IMAGE_FNV 0x4e154d31U        /* synthetic image word-FNV (record field) */
#define IMAGE_TICKS 0x1234U          /* synthetic MMU-off hash ticks */
#define SEG_OFF 32U                  /* LC_SEGMENT_64 command offset */
#define THREAD_OFF 104U              /* LC_UNIXTHREAD command offset */
#define ENTRY 0x4010U                /* synthetic entry offset */
#define ENTRY_WORD 0x14000001U       /* synthetic 'b .+4' at the entry */
#define NEW_VIRT 0xfffffe0006000000ULL
#define NEW_LINK 0xfffffe0007004000ULL
#define OLD_LINK 0xfffffff007004000ULL
#define FIXTURE_GROUPS 4
#define FIXTURE_VARIANTS 9
#define EXPECTED_CHECKS 9
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v319 fixture failed at line %d\n", __LINE__); \
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
    static uint8_t image[IMAGE_BYTES], bad[IMAGE_BYTES], args[N304_ARGS_BYTES];
    char text[N304_RECORD_BYTES + 1], host[N304_HOST_RECORD_BYTES + 1];
    char record[N304_HOST_RECORD_BYTES], altered[N304_HOST_RECORD_BYTES];
    static const char crumbs[] = "N315E1-\nN315B20\nN315M3-\n[0:";
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10, .args_hash = ARGS_FNV,
                                                 .adt_hash = ADT_FNV, .adt_nodes = ADT_NODES, .image_hash = IMAGE_FNV,
                                                 .entry_offset = ENTRY, .entry_word = ENTRY_WORD};
    uint32_t entry;
    int code = -2;

    /* Group 1: slid VM layout constants, builder VA rule and the N319PS20 format tags (record length 250). */
    CHECK((uint64_t)N311_VIRT_BASE == NEW_VIRT && N311_VIRT_BASE % 0x2000000 == 0);
    CHECK(N312_LINK_BASE == N311_VIRT_BASE + N311_KERNEL_OFFSET && N312_LINK_BASE == NEW_LINK);
    CHECK(((uint64_t)N311_VIRT_BASE >> 47) == 0x1ffff &&
          (((uint64_t)N311_VIRT_BASE + N311_KERNEL_OFFSET + 0x2000000 - 1) >> 47) == 0x1ffff);
    CHECK(snprintf(text, sizeof(text), N304_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_RECORD_BYTES &&
          snprintf(host, sizeof(host), N304_HOST_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_HOST_RECORD_BYTES &&
          N304_RECORD_BYTES == 250 && !memcmp(text, "N319PS20", 8) && !memcmp(text, host, sizeof(host)));

    /* Group 2: n311_arguments on the synthetic base: virtBase at +8, deviceTreeP = virtBase + kernel offset + image + 2048. */
    CHECK(n311_arguments(BASE, ADT_BYTES, IMAGE_BYTES, args) == N10_RT_OK && n312_le64(args + 8) == NEW_VIRT &&
          n312_le64(args + 16) == BASE && n312_le64(args + 96) == NEW_VIRT + 0x1004000 + IMAGE_BYTES + 2048 &&
          n312_le32(args + 104) == ADT_BYTES);

    /* Group 3: n312_entry_offset on a synthetic Mach-O slid to the new link base. */
    memset(image, 0, sizeof(image));
    n306_put32(image, N311_MH_MAGIC);
    n306_put32(image + 4, N311_MH_CPU_ARM64);
    n306_put32(image + 12, N311_MH_EXECUTE);
    n306_put32(image + 16, 2);                                  /* ncmds */
    n306_put32(image + 20, N312_SEGMENT_CMD_MIN + N312_THREAD_CMD_MIN); /* sizeofcmds */
    n306_put32(image + SEG_OFF, N312_LC_SEGMENT_64);
    n306_put32(image + SEG_OFF + 4, N312_SEGMENT_CMD_MIN);
    n306_put64(image + SEG_OFF + 24, NEW_LINK);                 /* slid executable segment vmaddr */
    n306_put64(image + SEG_OFF + 32, IMAGE_BYTES);              /* vmsize */
    n306_put32(image + SEG_OFF + 60, 5);                        /* initprot r-x */
    n306_put32(image + THREAD_OFF, N312_LC_UNIXTHREAD);
    n306_put32(image + THREAD_OFF + 4, N312_THREAD_CMD_MIN);
    n306_put32(image + THREAD_OFF + 8, N312_THREAD_FLAVOR);
    n306_put32(image + THREAD_OFF + 12, N312_THREAD_COUNT);
    n306_put64(image + THREAD_OFF + N312_THREAD_PC_OFFSET, NEW_LINK + ENTRY);
    n306_put32(image + ENTRY, ENTRY_WORD);
    entry = 0;
    CHECK(n312_entry_offset(image, IMAGE_BYTES, &entry) == 0 && entry == ENTRY);
    memcpy(bad, image, sizeof(bad));                            /* segment slid, pc left at the old link base */
    n306_put64(bad + THREAD_OFF + N312_THREAD_PC_OFFSET, OLD_LINK + ENTRY);
    entry = 0;
    CHECK(n312_entry_offset(bad, IMAGE_BYTES, &entry) == -1 && entry == 0);

    /* Group 4: N319PS2T validator with the unchanged N315 crumbs; an N318PS2T record is not a v319 witness. */
    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    make_record(record, "N319PS2");
    CHECK(n306_host_record_valid(record, sizeof(record), &expected) &&
          n315_crumb_trace(crumbs, sizeof(crumbs) - 1, &code) == 7 && code == 0);
    make_record(altered, "N318PS2");
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));

    if (checks != EXPECTED_CHECKS || FIXTURE_VARIANTS != EXPECTED_CHECKS || FIXTURE_GROUPS != 4) {
        fprintf(stderr, "v319 fixture check count %d\n", checks);
        return 1;
    }
    puts("v319 vm layout fixture PASS");
    return 0;
}
