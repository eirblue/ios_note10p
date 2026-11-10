#ifndef NOTE10_USER_INSTRUCTION_FETCH_H
#define NOTE10_USER_INSTRUCTION_FETCH_H

#include <stdint.h>
#include <mach/machine/thread_status.h>

enum n10_user_fetch_status {
    N10_USER_FETCH_OK,
    N10_USER_FETCH_BAD_STATE,
    N10_USER_FETCH_BAD_PC,
    N10_USER_FETCH_COPY_ERROR
};

struct n10_user_instruction {
    enum n10_user_fetch_status status;
    uint32_t word;
    int copy_error;
};

/* Caller owns a complete saved frame in its owning user task's address space.
 * A user-mode frame alone does not establish current_thread()->map ownership.
 * No frame writes, instruction dispatch, or production exception hook.
 * Failure returns word zero, including when copyin partially changed its local.
 */
struct n10_user_instruction
n10_fetch_user_instruction(const arm_saved_state_t *state);

#endif
