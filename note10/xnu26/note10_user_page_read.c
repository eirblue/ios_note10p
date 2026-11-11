#include "note10_user_page_read.h"

enum n10_user_page_status
n10_read_user_page_instruction(const struct n10_user_page_source *source,
                              uint64_t address, void *destination, size_t length)
{
    if (!source || !source->expected_task || !source->expected_map ||
        !source->current_task || !source->current_map ||
        source->expected_task != source->current_task ||
        source->expected_map != source->current_map)
        return N10_USER_PAGE_BAD_OWNER;

    if (!destination || !source->read4 || length != 4 || (address & 3) ||
        source->page_bytes != N10_USER_PAGE_BYTES ||
        source->page_address % N10_USER_PAGE_BYTES ||
        source->page_address > UINT64_MAX - source->page_bytes ||
        address < source->page_address ||
        address - source->page_address > source->page_bytes - 4)
        return N10_USER_PAGE_BAD_REQUEST;

    if (((source->maxprot | source->initprot) & ~UINT32_C(7)) ||
        (source->initprot & ~source->maxprot) ||
        (source->initprot & UINT32_C(5)) != UINT32_C(5))
        return N10_USER_PAGE_BAD_RIGHTS;

    unsigned char bytes[4] = {0};
    if (source->read4(source->context, address - source->page_address, bytes))
        return N10_USER_PAGE_READ_FAILED;

    unsigned char *output = destination;
    for (size_t index = 0; index < sizeof(bytes); ++index)
        output[index] = bytes[index];
    return N10_USER_PAGE_OK;
}
