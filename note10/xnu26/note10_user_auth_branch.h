#ifndef NOTE10_USER_AUTH_BRANCH_H
#define NOTE10_USER_AUTH_BRANCH_H

#include "note10_user_instruction_fetch.h"
#include "../compat/auth_branch.h"

enum n10_user_branch_status {
    N10_USER_BRANCH_FETCH_FAILED,
    N10_USER_BRANCH_UNSUPPORTED,
    N10_USER_BRANCH_DECODED
};

struct n10_user_branch_decode {
    enum n10_user_branch_status status;
    struct n10_user_instruction fetch;
    struct n10_auth_branch branch;
};

/* The caller retains the fetch API's frame and owning user-task map contract.
 * This returns a descriptor only; it does not authenticate or change state.
 * The branch descriptor remains zero on fetch failure or unsupported input.
 */
struct n10_user_branch_decode
n10_decode_user_auth_branch(const arm_saved_state_t *state);

#endif
