#ifndef NOTE10_MODEL_USER_ENTRY_FRAME_H
#define NOTE10_MODEL_USER_ENTRY_FRAME_H

#include <sys/types.h>
#include "note10_user_instruction_fetch.h"

struct n10_model_user_entry_request {
    uint64_t raw_page_address;
    uint64_t raw_entry_pc;
    uint64_t page_bytes;
    uint64_t model_load_bias;
};

struct n10_model_user_entry_frame {
    arm_saved_state_t state;
    uint64_t page_address;
};

enum n10_model_entry_status {
    N10_MODEL_ENTRY_OK,
    N10_MODEL_ENTRY_INVALID,
    N10_MODEL_ENTRY_RANGE,
    N10_MODEL_ENTRY_OVERFLOW
};

/* Controlled LP64/non-PAC reference-model values for the fetch interface.
 * The caller owns request/output for this synchronous operation.
 * Failure leaves every output byte unchanged. Success zeroes all other frame
 * fields; zero SP/LR are fetch data and do not describe a launch stack.
 * No ASLR choice, runtime slide, task/map, mapping or execution is established.
 */
enum n10_model_entry_status
n10_make_model_user_entry_frame(const struct n10_model_user_entry_request *request,
                               struct n10_model_user_entry_frame *output);

#endif
