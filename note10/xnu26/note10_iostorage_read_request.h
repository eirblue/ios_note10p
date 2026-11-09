#ifndef NOTE10_IOSTORAGE_READ_REQUEST_H
#define NOTE10_IOSTORAGE_READ_REQUEST_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum note10_iostorage_read_status {
    NOTE10_IOSTORAGE_READ_OK,
    NOTE10_IOSTORAGE_READ_SHORT,
    NOTE10_IOSTORAGE_READ_ERROR
};

/* Read synchronously into the caller's destination in context. Set *actual_bytes
 * to the transferred byte count, including on failure. Return true on success. */
typedef bool (*note10_iostorage_backing_read)(void *context, uint64_t byte_offset,
                                            uint64_t byte_length, uint64_t *actual_bytes);
typedef void (*note10_iostorage_read_completion)(void *context,
                                                enum note10_iostorage_read_status status,
                                                uint64_t actual_bytes);

/* True means admitted. An admitted request calls read, then complete, once each
 * before returning. Rejection calls neither. The descriptor length must equal
 * the request size. A successful short read reports SHORT and the transferred
 * bytes. A backing failure reports ERROR and the transferred bytes. An
 * out-of-range callback count reports ERROR with zero bytes. */
bool note10_iostorage_read_request(uint64_t extent_bytes, uint64_t block_bytes,
                                 uint64_t lba, uint64_t count,
                                 uint64_t descriptor_length, uint32_t direction,
                                 note10_iostorage_backing_read read,
                                 note10_iostorage_read_completion complete,
                                 void *context);

#ifdef __cplusplus
}
#endif

#endif
