#ifndef NOTE10_USER_PAGE_READ_H
#define NOTE10_USER_PAGE_READ_H

#include <stddef.h>
#include <stdint.h>

#define N10_USER_PAGE_BYTES UINT64_C(16384)

/* Zero means all four bytes were produced. A failure must return nonzero. */
typedef int (*n10_user_page_read4)(void *context, uint64_t offset, unsigned char bytes[4]);

struct n10_user_page_source {
    const void *expected_task;
    const void *expected_map;
    const void *current_task;
    const void *current_map;
    uint64_t page_address;
    uint64_t page_bytes;
    uint32_t maxprot;
    uint32_t initprot;
    n10_user_page_read4 read4;
    void *context;
};

enum n10_user_page_status {
    N10_USER_PAGE_OK,
    N10_USER_PAGE_BAD_OWNER,
    N10_USER_PAGE_BAD_REQUEST,
    N10_USER_PAGE_BAD_RIGHTS,
    N10_USER_PAGE_READ_FAILED
};

/* The synchronous caller retains source, token and callback lifetimes.
 * Tokens express caller-supplied identity equality, with no task/map attestation.
 * This read service grants no mapping, instruction execution or input authority.
 * Destination stays unchanged on denial or callback failure.
 */
enum n10_user_page_status
n10_read_user_page_instruction(const struct n10_user_page_source *source,
                              uint64_t address, void *destination, size_t length);

#endif
