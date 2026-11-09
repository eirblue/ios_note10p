#ifndef NOTE10_IOSTORAGE_READ_RANGE_H
#define NOTE10_IOSTORAGE_READ_RANGE_H

#include <stdbool.h>
#include <stdint.h>

enum { NOTE10_IOSTORAGE_READ_DIRECTION = 1 }; /* kIODirectionIn */

struct note10_iostorage_range {
    uint64_t byte_offset;
    uint64_t byte_length;
    uint64_t max_lba;
};

#ifdef __cplusplus
extern "C" {
#endif

/* Translate a read using the caller's IOMemoryDescriptor direction and
 * backing geometry. Offsets are relative to the backing start. max_lba is
 * inclusive. Rejection preserves the output. */
bool note10_iostorage_read_range(uint64_t extent_bytes, uint64_t block_bytes,
                                 uint64_t lba, uint64_t count, uint32_t direction,
                                 struct note10_iostorage_range *out);

#ifdef __cplusplus
}
#endif

#endif
