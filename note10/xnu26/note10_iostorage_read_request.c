#include <stddef.h>

#include "note10_iostorage_read_range.h"
#include "note10_iostorage_read_request.h"

bool
note10_iostorage_read_request(uint64_t extent_bytes, uint64_t block_bytes,
                             uint64_t lba, uint64_t count,
                             uint64_t descriptor_length, uint32_t direction,
                             note10_iostorage_backing_read read,
                             note10_iostorage_read_completion complete,
                             void *context)
{
    struct note10_iostorage_range range;
    if (read == NULL || complete == NULL ||
        !note10_iostorage_read_range(extent_bytes, block_bytes, lba, count, direction, &range) ||
        descriptor_length != range.byte_length)
        return false;

    uint64_t actual_bytes = 0;
    bool success = read(context, range.byte_offset, range.byte_length, &actual_bytes);
    enum note10_iostorage_read_status status = NOTE10_IOSTORAGE_READ_ERROR;

    if (actual_bytes > range.byte_length) {
        actual_bytes = 0;
    } else if (success) {
        status = actual_bytes == range.byte_length ?
            NOTE10_IOSTORAGE_READ_OK : NOTE10_IOSTORAGE_READ_SHORT;
    }

    complete(context, status, actual_bytes);
    return true;
}
