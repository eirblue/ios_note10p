#include "import_table.h"

static uint32_t u32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static uint64_t u64(const uint8_t *p)
{
    return (uint64_t)u32(p) | (uint64_t)u32(p + 4) << 32;
}
static int64_t signed64(uint64_t v)
{
    return v <= INT64_MAX ? (int64_t)v : -1 - (int64_t)(~v);
}

enum n10_import_result n10_import_at(const uint8_t *blob, size_t size,
                                     uint32_t index, struct n10_import *out)
{
    if (!blob || !out)
        return N10_IMPORT_BAD_INPUT;
    if (size < 28)
        return N10_IMPORT_BOUNDS;
    uint32_t version = u32(blob), imports = u32(blob + 8), symbols = u32(blob + 12);
    uint32_t count = u32(blob + 16), format = u32(blob + 20), symbol_format = u32(blob + 24);
    if (version != 0 || symbol_format != 0 || format < 1 || format > 3)
        return N10_IMPORT_UNSUPPORTED;
    size_t stride = format == 1 ? 4 : (format == 2 ? 8 : 16);
    if (index >= count || imports < 28 || imports > size || symbols < 28 || symbols > size)
        return N10_IMPORT_BOUNDS;
    if (count > (size - imports) / stride)
        return N10_IMPORT_BOUNDS;
    size_t table_end = imports + (size_t)count * stride;
    if (symbols < table_end)
        return N10_IMPORT_ENCODING; /* Reject overlapping import/string tables. */
    const uint8_t *entry = blob + imports + (size_t)index * stride;
    struct n10_import d = {0};
    uint32_t name_offset;
    if (format == 3) {
        uint64_t bits = u64(entry);
        if ((bits >> 17) & 0x7fff)
            return N10_IMPORT_ENCODING;
        uint32_t ordinal = (uint32_t)(bits & 0xffff);
        d.library_ordinal = ordinal <= 0xfff0 ? (int32_t)ordinal : (int32_t)ordinal - 0x10000;
        d.weak = (uint8_t)((bits >> 16) & 1);
        name_offset = (uint32_t)(bits >> 32);
        d.addend = signed64(u64(entry + 8));
    } else {
        uint32_t bits = u32(entry), ordinal = bits & 0xff;
        d.library_ordinal = ordinal <= 0xf0 ? (int32_t)ordinal : (int32_t)ordinal - 0x100;
        d.weak = (uint8_t)((bits >> 8) & 1);
        name_offset = bits >> 9;
        if (format == 2) {
            uint32_t addend = u32(entry + 4);
            d.addend = addend <= INT32_MAX ? (int32_t)addend : -1 - (int64_t)(~addend);
        }
    }
    if (name_offset >= size - symbols)
        return N10_IMPORT_BOUNDS;
    size_t start = symbols + (size_t)name_offset, end = start;
    while (end < size && blob[end])
        ++end;
    if (end == size)
        return N10_IMPORT_BOUNDS;
    if (end == start)
        return N10_IMPORT_ENCODING;
    d.name = (const char *)(blob + start);
    d.name_length = end - start;
    *out = d;
    return N10_IMPORT_OK;
}
