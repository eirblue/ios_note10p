#include "note10_user_auth_branch.h"

struct n10_user_branch_decode
n10_decode_user_auth_branch(const arm_saved_state_t *state)
{
    struct n10_user_branch_decode result = {.status = N10_USER_BRANCH_FETCH_FAILED};
    result.fetch = n10_fetch_user_instruction(state);
    if (result.fetch.status != N10_USER_FETCH_OK)
        return result;

    result.status = N10_USER_BRANCH_UNSUPPORTED;
    struct n10_auth_branch decoded = {0};
    if (!n10_decode_auth_branch(result.fetch.word, &decoded))
        return result;

    result.branch = decoded;
    result.status = N10_USER_BRANCH_DECODED;
    return result;
}
