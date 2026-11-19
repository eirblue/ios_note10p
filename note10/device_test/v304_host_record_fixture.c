/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include "v304_host_record_validate.h"

#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

static void put_hex(char *field, size_t digits, uint64_t value)
{
    static const char hex[] = "0123456789abcdef";

    while (digits) {
        field[--digits] = hex[value & 15];
        value >>= 4;
    }
}

static void seal(char *record)
{
    put_hex(record + N304_HOST_CSUM_OFFSET, 8, n304_host_body_checksum(record));
}

int main(void)
{
    struct n304_host_record_expected expected = {.x0 = N304_HOST_ARENA_ALIGNMENT};
    char formatted[N304_HOST_RECORD_BYTES + 1];
    char record[N304_HOST_RECORD_BYTES], altered[N304_HOST_RECORD_BYTES];
    const struct {
        size_t offset;
        char byte;
    } invalid_field[] = {
        {0, 'X'},
        {N304_HOST_COMMIT_OFFSET, N304_HOST_PENDING},
        {N304_HOST_LF_OFFSET, '\r'},
        {N304_HOST_BUILD_OFFSET, '2'},
        {N304_HOST_BOOT_OFFSET, '3'},
        {N304_HOST_ATTEMPT_OFFSET, '4'},
        {N304_HOST_BUILD_OFFSET + N304_HOST_ID_HEX_DIGITS, '1'},
        {N304_HOST_REG_OFFSET + 16, ';'},
        {N304_HOST_REG_OFFSET + 12, '8'},
        {N304_HOST_REG_OFFSET + N304_HOST_REG_STRIDE + 15, '1'},
        {N304_HOST_REG_OFFSET + 2 * N304_HOST_REG_STRIDE + 15, '1'},
        {N304_HOST_REG_OFFSET + 3 * N304_HOST_REG_STRIDE + 15, 'F'},
        {N304_HOST_ARGS_HASH_OFFSET, 'A'},
        {N304_HOST_ADT_HASH_OFFSET, 'g'},
        {N304_HOST_ADT_LENGTH_OFFSET + 1, '4'},
        {N304_HOST_EL_OFFSET, '2'},
        {N304_HOST_SCTLR_OFFSET + 15, '1'},
        {N304_HOST_SCTLR_OFFSET + 15, '4'},
        {N304_HOST_SCTLR_OFFSET + 12, '1'},
        {N304_HOST_DAIF_OFFSET, 'e'}
    };

    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    int bytes = snprintf(formatted, sizeof(formatted), N304_HOST_FORMAT,
                         BUILD_ID, BOOT_ID, ATTEMPT_ID);
    assert(bytes == N304_HOST_RECORD_BYTES);
    memcpy(record, formatted, sizeof(record));
    put_hex(record + N304_HOST_REG_OFFSET, 16, expected.x0);
    put_hex(record + N304_HOST_REG_OFFSET + 3 * N304_HOST_REG_STRIDE, 16, 0xfeed);
    put_hex(record + N304_HOST_ADT_LENGTH_OFFSET, 2, N304_HOST_ADT_MIN_BYTES);
    record[N304_HOST_EL_OFFSET] = '1';
    record[N304_HOST_DAIF_OFFSET] = 'f';
    assert(n304_host_body_checksum(record) == UINT32_C(0xae9d2f6e));
    seal(record);
    record[N304_HOST_COMMIT_OFFSET] = N304_HOST_COMMITTED;
    assert(n304_host_record_valid(record, sizeof(record), &expected));
    assert(!n304_host_record_valid(record, sizeof(record) - 1, &expected));
    memcpy(formatted, record, sizeof(record));
    assert(!n304_host_record_valid(formatted, sizeof(formatted), &expected));

    for (size_t i = 0; i < sizeof(invalid_field) / sizeof(invalid_field[0]); ++i) {
        memcpy(altered, record, sizeof(altered));
        altered[invalid_field[i].offset] = invalid_field[i].byte;
        seal(altered);
        assert(!n304_host_record_valid(altered, sizeof(altered), &expected));
    }

    memcpy(altered, record, sizeof(altered));
    put_hex(altered + N304_HOST_ADT_LENGTH_OFFSET, 2, N304_HOST_ADT_MAX_BYTES);
    seal(altered);
    assert(n304_host_record_valid(altered, sizeof(altered), &expected));
    put_hex(altered + N304_HOST_ADT_LENGTH_OFFSET, 2, N304_HOST_ADT_MAX_BYTES + 4);
    seal(altered);
    assert(!n304_host_record_valid(altered, sizeof(altered), &expected));
    put_hex(altered + N304_HOST_ADT_LENGTH_OFFSET, 2, N304_HOST_ADT_MIN_BYTES + 1);
    seal(altered);
    assert(!n304_host_record_valid(altered, sizeof(altered), &expected));

    memcpy(altered, record, sizeof(altered));
    expected.build[0] = 'A';
    altered[N304_HOST_BUILD_OFFSET] = 'A';
    seal(altered);
    assert(!n304_host_record_valid(altered, sizeof(altered), &expected));
    expected.build[0] = BUILD_ID[0];

    memcpy(altered, record, sizeof(altered));
    altered[N304_HOST_CSUM_OFFSET] = altered[N304_HOST_CSUM_OFFSET] == '0' ? '1' : '0';
    assert(!n304_host_record_valid(altered, sizeof(altered), &expected));

    expected.x0 = 0;
    put_hex(altered + N304_HOST_REG_OFFSET, 16, expected.x0);
    seal(altered);
    assert(!n304_host_record_valid(altered, sizeof(altered), &expected));
    expected.x0 = N304_HOST_ARENA_ALIGNMENT + 1;
    put_hex(altered + N304_HOST_REG_OFFSET, 16, expected.x0);
    seal(altered);
    assert(!n304_host_record_valid(altered, sizeof(altered), &expected));

    puts("v304 synthetic host record PASS");
    return 0;
}
