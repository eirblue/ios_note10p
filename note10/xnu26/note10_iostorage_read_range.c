#include <stddef.h>

#include "note10_iostorage_read_range.h"

bool
note10_iostorage_read_range(uint64_t extent_bytes, uint64_t block_bytes,
                            uint64_t lba, uint64_t count, uint32_t direction,
                            struct note10_iostorage_range *out)
{
    if (out == NULL || direction != NOTE10_IOSTORAGE_READ_DIRECTION ||
        extent_bytes == 0 || block_bytes == 0 || count == 0 || extent_bytes % block_bytes != 0)
        return false;

    uint64_t blocks = extent_bytes / block_bytes;
    if (lba >= blocks || count > blocks - lba)
        return false;

    /* Each product and the exclusive byte end are bounded by extent_bytes. */
    out->byte_offset = lba * block_bytes;
    out->byte_length = count * block_bytes;
    out->max_lba = blocks - 1;
    return true;
}
