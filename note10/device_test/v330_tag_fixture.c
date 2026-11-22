/* SPDX-License-Identifier: GPL-2.0-only */
/* v330 host fixture (new cases only): the N330PS20 kernel and host record format tags with the unchanged 250-byte record,
 * and the N330PS2T validator with the unchanged N315 crumbs (an N329PS2T record is rejected). Synthetic values only:
 * synthetic window base and record fields; no real kernel bytes, entry, address or register. */
#include <stdio.h>
#include "v330_abi_contract.h"
#include "v330_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 32 MiB-aligned window base >= 2 GiB */
#define MPIDR 0x81000010ULL          /* synthetic raw MPIDR: affinity 0x10 */
#define ADT_NODES 14U
#define ADT_FNV 0xc1cb3618U          /* synthetic record field */
#define ARGS_FNV 0xaee810a3U         /* synthetic record field */
#define IMAGE_FNV 0x4e154d31U        /* synthetic image word-FNV (record field) */
#define IMAGE_TICKS 0x1234U          /* synthetic MMU-off hash ticks */
#define ENTRY 0x4010U                /* synthetic entry offset */
#define ENTRY_WORD 0x14000001U       /* synthetic 'b .+4' at the entry */
#define FIXTURE_GROUPS 2
#define FIXTURE_VARIANTS 4
#define EXPECTED_CHECKS 4
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v330 fixture failed at line %d\n", __LINE__); \
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
    char text[N304_RECORD_BYTES + 1], host[N304_HOST_RECORD_BYTES + 1];
    char record[N304_HOST_RECORD_BYTES], altered[N304_HOST_RECORD_BYTES];
    static const char crumbs[] = "N315E1-\nN315B20\nN315M3-\n[0:";
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10, .args_hash = ARGS_FNV,
                                                 .adt_hash = ADT_FNV, .adt_nodes = ADT_NODES, .image_hash = IMAGE_FNV,
                                                 .entry_offset = ENTRY, .entry_word = ENTRY_WORD};
    int code = -2;

    /* Group 1: kernel and host record format tags N330PS20; the record length stays 250. */
    CHECK(snprintf(text, sizeof(text), N304_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_RECORD_BYTES &&
          N304_RECORD_BYTES == 250 && !memcmp(text, "N330PS20", 8));
    CHECK(snprintf(host, sizeof(host), N304_HOST_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_HOST_RECORD_BYTES &&
          N304_HOST_RECORD_BYTES == 250 && !memcmp(host, "N330PS20", 8) && !memcmp(text, host, sizeof(host)));

    /* Group 2: N330PS2T validator with the unchanged N315 crumbs; an N329PS2T record is not a v330 witness. */
    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    make_record(record, "N330PS2");
    CHECK(n306_host_record_valid(record, sizeof(record), &expected) &&
          n315_crumb_trace(crumbs, sizeof(crumbs) - 1, &code) == 7 && code == 0);
    make_record(altered, "N329PS2");
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));

    if (checks != EXPECTED_CHECKS || FIXTURE_VARIANTS != EXPECTED_CHECKS || FIXTURE_GROUPS != 2) {
        fprintf(stderr, "v330 fixture check count %d\n", checks);
        return 1;
    }
    puts("v330 tag fixture PASS");
    return 0;
}
