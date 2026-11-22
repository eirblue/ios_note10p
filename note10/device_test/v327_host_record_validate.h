/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N327_HOST_RECORD_VALIDATE_H
#define N327_HOST_RECORD_VALIDATE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "v327_host_record.h"

enum {
    N311_HOST_WINDOW_ALIGNMENT = 0x2000000,
    N306_HOST_SCTLR_MCI = 0x1005
};

#define N306_HOST_MPIDR_MASK 0xff00ffffffULL

struct n306_host_record_expected {
    char build[N304_HOST_ID_HEX_DIGITS];
    char boot[N304_HOST_ID_HEX_DIGITS];
    char attempt[N304_HOST_ID_HEX_DIGITS];
    uint64_t x0, mpidr_aff;
    uint32_t args_hash, adt_hash, adt_nodes, image_hash, entry_offset, entry_word;
};

static inline bool n306_host_read_hex(const char *field, size_t digits, uint64_t *out)
{
    static const char hex[] = "0123456789abcdef";
    uint64_t value = 0;

    for (size_t i = 0; i < digits; ++i) {
        const char *digit = memchr(hex, (unsigned char)field[i], sizeof(hex) - 1);
        if (!digit)
            return false;
        value = (value << 4) | (uint64_t)(digit - hex);
    }
    if (out)
        *out = value;
    return true;
}

static inline uint32_t n306_host_body_checksum(const char *record)
{
    uint32_t hash = N304_HOST_FNV_INIT;

    for (size_t i = 0; i < N304_HOST_BODY_BYTES; ++i)
        hash = (hash ^ (unsigned char)record[N304_HOST_BODY_OFFSET + i]) * N304_HOST_FNV_PRIME;
    return hash;
}

/* Same framing as the v304 validator with tag N327PS2 (an N326PS2T record is not a v327 witness). r[0] is the 32 MiB-aligned window base, r[1] is raw MPIDR
 * (affinity must match), r[2] low 32 bits must equal the expected image hash and its high 32 bits (ticks) be nonzero,
 * r[3] high 32 bits must equal the expected nonzero 4-aligned entry_offset and its low 32 bits the expected entry word,
 * and a/d/n(node count) must equal the pre-actor expectations. */
static inline bool n306_host_record_valid(const char *record, size_t bytes,
                                          const struct n306_host_record_expected *expected)
{
    static const size_t id_offsets[] = {
        N304_HOST_BUILD_OFFSET, N304_HOST_BOOT_OFFSET, N304_HOST_ATTEMPT_OFFSET
    };
    uint64_t regs[4], args, adt, words, sctlr, checksum;

    if (!record || bytes != N304_HOST_RECORD_BYTES || !expected)
        return false;
    if (memcmp(record, "N327PS2", N304_HOST_COMMIT_OFFSET) ||
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
        if (!n306_host_read_hex(id, N304_HOST_ID_HEX_DIGITS, NULL) ||
            memcmp(id, ids[i], N304_HOST_ID_HEX_DIGITS))
            return false;
    }
    for (size_t i = 0; i < sizeof(regs) / sizeof(regs[0]); ++i) {
        const char *field = record + N304_HOST_REG_OFFSET + i * N304_HOST_REG_STRIDE;
        if ((i && field[-1] != ',') || !n306_host_read_hex(field, 16, &regs[i]))
            return false;
    }
    if (!n306_host_read_hex(record + N304_HOST_ARGS_HASH_OFFSET, 8, &args) ||
        !n306_host_read_hex(record + N304_HOST_ADT_HASH_OFFSET, 8, &adt) ||
        !n306_host_read_hex(record + N304_HOST_ADT_LENGTH_OFFSET, 2, &words) ||
        !n306_host_read_hex(record + N304_HOST_SCTLR_OFFSET, 16, &sctlr) ||
        !n306_host_read_hex(record + N304_HOST_CSUM_OFFSET, 8, &checksum))
        return false;

    return regs[0] && regs[0] % N311_HOST_WINDOW_ALIGNMENT == 0 && regs[0] == expected->x0 &&
           (regs[1] & N306_HOST_MPIDR_MASK) == expected->mpidr_aff &&
           expected->entry_offset && expected->entry_offset % 4 == 0 && (regs[3] >> 32) == expected->entry_offset &&
           (regs[3] & 0xffffffffULL) == expected->entry_word &&
           (regs[2] & 0xffffffffULL) == expected->image_hash && (regs[2] >> 32) != 0 &&
           args == expected->args_hash && adt == expected->adt_hash && words == expected->adt_nodes &&
           record[N304_HOST_EL_OFFSET] == '1' && (sctlr & N306_HOST_SCTLR_MCI) == 0 &&
           record[N304_HOST_DAIF_OFFSET] == 'f' && checksum == n306_host_body_checksum(record);
}

/* v315: checkpoint trace from the bytes that follow the record LF. Up to three consecutive 8-byte crumbs, each one of
 * C1 / C2 / C3 in any order and at most once; C2's value byte must be a lowercase hex digit. Parsing stops at the first
 * byte run that is not a new valid crumb (a truncated crumb counts as absent). Returns the mask (1 = C1, 2 = C2, 4 = C3)
 * and *builder_code = the C2 digit value, or -1 without C2. */
static inline int n315_crumb_trace(const char *after, size_t len, int *builder_code)
{
    static const char hex[] = "0123456789abcdef";
    int mask = 0, code = -1, bit;
    size_t at;

    for (at = 0; after && at < 3 * N315_HOST_CRUMB_BYTES && len >= at + N315_HOST_CRUMB_BYTES;
         at += N315_HOST_CRUMB_BYTES) {
        const char *crumb = after + at;
        const char *digit = NULL;

        if (!memcmp(crumb, N315_HOST_C1, N315_HOST_CRUMB_BYTES))
            bit = 1;
        else if (!memcmp(crumb, N315_HOST_C3, N315_HOST_CRUMB_BYTES))
            bit = 4;
        else if (!memcmp(crumb, N315_HOST_C2_PREFIX, 6) && crumb[7] == '\n' &&
                 (digit = memchr(hex, (unsigned char)crumb[6], sizeof(hex) - 1)) != NULL)
            bit = 2;
        else
            break;
        if (mask & bit)
            break;
        mask |= bit;
        if (digit)
            code = (int)(digit - hex);
    }
    if (builder_code)
        *builder_code = code;
    return mask;
}

#endif
