#include "note10_model_user_entry_frame.h"
#include "note10_user_page_read.h"
#include <arm64/proc_reg.h>
#include <string.h>

enum n10_model_entry_status
n10_make_model_user_entry_frame(const struct n10_model_user_entry_request *request,
                               struct n10_model_user_entry_frame *output)
{
    if (!request || !output || request->page_bytes != N10_USER_PAGE_BYTES ||
        request->raw_page_address % N10_USER_PAGE_BYTES ||
        request->model_load_bias % N10_USER_PAGE_BYTES)
        return N10_MODEL_ENTRY_INVALID;
    if (request->raw_page_address > UINT64_MAX - N10_USER_PAGE_BYTES)
        return N10_MODEL_ENTRY_OVERFLOW;
    if ((request->raw_entry_pc & 3) || request->raw_entry_pc < request->raw_page_address ||
        request->raw_entry_pc - request->raw_page_address > N10_USER_PAGE_BYTES - 4)
        return N10_MODEL_ENTRY_RANGE;
    if (request->model_load_bias > UINT64_MAX - request->raw_page_address)
        return N10_MODEL_ENTRY_OVERFLOW;

    uint64_t page_address = request->raw_page_address + request->model_load_bias;
    if (page_address > UINT64_MAX - N10_USER_PAGE_BYTES)
        return N10_MODEL_ENTRY_OVERFLOW;
    uint64_t offset = request->raw_entry_pc - request->raw_page_address;
    struct n10_model_user_entry_frame built;
    memset(&built, 0, sizeof(built));
    built.page_address = page_address;
    built.state.ash.flavor = ARM_SAVED_STATE64;
    built.state.ash.count = ARM_SAVED_STATE64_COUNT;
    built.state.ss_64.pc = page_address + offset;
    built.state.ss_64.cpsr = PSR64_MODE_EL0;
    memcpy(output, &built, sizeof(built));
    return N10_MODEL_ENTRY_OK;
}
