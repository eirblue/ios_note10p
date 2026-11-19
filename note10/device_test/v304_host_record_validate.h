/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N304_HOST_RECORD_VALIDATE_H
#define N304_HOST_RECORD_VALIDATE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "v304_host_record.h"

enum {
    N304_HOST_ARENA_ALIGNMENT = 16384,
    N304_HOST_ADT_MIN_BYTES = 104,
    N304_HOST_ADT_MAX_BYTES = 164,
    N304_HOST_SCTLR_MCI = 0x1005
};

struct n304_host_record_expected {
    char build[N304_HOST_ID_HEX_DIGITS];
    char boot[N304_HOST_ID_HEX_DIGITS];
    char attempt[N304_HOST_ID_HEX_DIGITS];
    uint64_t x0;
};

static inline bool n304_host_read_hex(const char *field, size_t digits, uint64_t *out)
{
    static const char hex[] = "0123456789abcdef";
    uint64_t value = 0;

    for (size_t i = 0; i < digits; ++i) {
        const char *digit = memchr(hex, (unsigned char)field[i], sizeof(hex) - 1);
        if (!digit)
            return false;
        if (out)
            value = (value << 4) | (uint64_t)(digit - hex);
    }
    if (out)
        *out = value;
    return true;
}

static inline uint32_t n304_host_body_checksum(const char *record)
{
    uint32_t hash = N304_HOST_FNV_INIT;

    for (size_t i = 0; i < N304_HOST_BODY_BYTES; ++i)
        hash = (hash ^ (unsigned char)record[N304_HOST_BODY_OFFSET + i]) * N304_HOST_FNV_PRIME;
    return hash;
}

static inline bool n304_host_record_valid(const char *record, size_t bytes,
                                          const struct n304_host_record_expected *expected)
{
    static const size_t id_offsets[] = {
        N304_HOST_BUILD_OFFSET, N304_HOST_BOOT_OFFSET, N304_HOST_ATTEMPT_OFFSET
    };
    uint64_t regs[4], adt_bytes, sctlr, checksum;

    if (!record || bytes != N304_HOST_RECORD_BYTES || !expected)
        return false;
    if (memcmp(record, "N304PS2", N304_HOST_COMMIT_OFFSET) ||
        record[N304_HOST_COMMIT_OFFSET] != N304_HOST_COMMITTED ||
        memcmp(record + N304_HOST_BUILD_OFFSET - 4, " id=", 4) ||
        memcmp(record + N304_HOST_BOOT_OFFSET - 3, " b=", 3) ||
        memcmp(record + N304_HOST_ATTEMPT_OFFSET - 3, " c=", 3) ||
        memcmp(record + N304_HOST_REG_OFFSET - 3, " r=", 3) ||
        memcmp(record + N304_HOST_ARGS_HASH_OFFSET - 3, " a=", 3) ||
        memcmp(record + N304_HOST_ADT_HASH_OFFSET - 3, " d=", 3) ||
        memcmp(record + N304_HOST_ADT_LENGTH_OFFSET - 3, " n=", 3) ||
        memcmp(record + N304_HOST_DAIF_OFFSET - 3, " q=", 3) ||
        memcmp(record + N304_HOST_SCTLR_OFFSET - 3, " s=", 3) ||
        memcmp(record + N304_HOST_EL_OFFSET - 3, " e=", 3) ||
        memcmp(record + N304_HOST_CSUM_OFFSET - 3, " f=", 3) ||
        record[N304_HOST_LF_OFFSET] != '\n')
        return false;

    const char *const ids[] = {expected->build, expected->boot, expected->attempt};
    for (size_t i = 0; i < sizeof(id_offsets) / sizeof(id_offsets[0]); ++i) {
        const char *id = record + id_offsets[i];
        if (!n304_host_read_hex(id, N304_HOST_ID_HEX_DIGITS, NULL) ||
            memcmp(id, ids[i], N304_HOST_ID_HEX_DIGITS))
            return false;
    }

    for (size_t i = 0; i < sizeof(regs) / sizeof(regs[0]); ++i) {
        const char *field = record + N304_HOST_REG_OFFSET + i * N304_HOST_REG_STRIDE;
        if ((i && field[-1] != ',') || !n304_host_read_hex(field, 16, &regs[i]))
            return false;
    }

    if (!n304_host_read_hex(record + N304_HOST_ARGS_HASH_OFFSET, 8, NULL) ||
        !n304_host_read_hex(record + N304_HOST_ADT_HASH_OFFSET, 8, NULL) ||
        !n304_host_read_hex(record + N304_HOST_ADT_LENGTH_OFFSET, 2, &adt_bytes) ||
        !n304_host_read_hex(record + N304_HOST_SCTLR_OFFSET, 16, &sctlr) ||
        !n304_host_read_hex(record + N304_HOST_CSUM_OFFSET, 8, &checksum))
        return false;

    return regs[0] && regs[0] % N304_HOST_ARENA_ALIGNMENT == 0 &&
           regs[0] == expected->x0 && regs[1] == 0 && regs[2] == 0 &&
           adt_bytes >= N304_HOST_ADT_MIN_BYTES && adt_bytes <= N304_HOST_ADT_MAX_BYTES &&
           adt_bytes % 4 == 0 && record[N304_HOST_EL_OFFSET] == '1' &&
           (sctlr & N304_HOST_SCTLR_MCI) == 0 && record[N304_HOST_DAIF_OFFSET] == 'f' &&
           checksum == n304_host_body_checksum(record);
}

#endif
