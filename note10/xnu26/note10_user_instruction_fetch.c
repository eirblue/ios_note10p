#include <sys/types.h>
#include "note10_user_instruction_fetch.h"
#include <arm64/proc_reg.h>
#include <libkern/copyio.h>

_Static_assert(sizeof(user_addr_t) == sizeof(uint64_t), "64-bit user address required");
_Static_assert(sizeof(register_t) == sizeof(uint64_t), "64-bit saved PC required");
_Static_assert(sizeof(uint32_t) == 4, "four-byte instruction required");

struct n10_user_instruction
n10_fetch_user_instruction(const arm_saved_state_t *state)
{
    struct n10_user_instruction result = {N10_USER_FETCH_BAD_STATE, 0, 0};
    if (!state || !is_saved_state64(state) ||
        state->ash.count != ARM_SAVED_STATE64_COUNT ||
        !PSR64_IS_USER64(get_saved_state_cpsr(state)))
        return result;

    uint64_t pc = (uint64_t)get_saved_state_pc(state);
    if ((pc & 3) || pc > UINT64_MAX - 3) {
        result.status = N10_USER_FETCH_BAD_PC;
        return result;
    }

    uint32_t word = 0;
    result.copy_error = copyin((user_addr_t)pc, &word, sizeof(word));
    if (result.copy_error) {
        result.status = N10_USER_FETCH_COPY_ERROR;
        return result;
    }
    result.status = N10_USER_FETCH_OK;
    result.word = word;
    return result;
}
