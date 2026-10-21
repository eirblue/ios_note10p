#ifndef NOTE10_IMPORT_TABLE_H
#define NOTE10_IMPORT_TABLE_H
#include <stddef.h>
#include <stdint.h>
struct n10_import {
    int32_t library_ordinal;
    uint8_t weak;
    int64_t addend;
    const char *name; /* Borrowed from the immutable fixup blob. */
    size_t name_length;
};
enum n10_import_result {
    N10_IMPORT_OK, N10_IMPORT_BAD_INPUT, N10_IMPORT_BOUNDS,
    N10_IMPORT_UNSUPPORTED, N10_IMPORT_ENCODING
};
/* Formats 1/2/3; version 0 and uncompressed symbol pool only. This validates
 * the import table/name being read, not other structures in the fixup payload.
 * No symbol lookup/relocation is performed. *out is unchanged on error.
 */
enum n10_import_result n10_import_at(const uint8_t *blob, size_t size,
                                     uint32_t index, struct n10_import *out);
#endif
