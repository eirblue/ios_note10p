#include "note10_user_auth_branch.h"
#include <arm64/proc_reg.h>
#include <libkern/copyio.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

static unsigned calls, bad_call, cases;
static uint64_t expected_address;
static uint32_t supplied_word;
static int copy_error, partial_copy;

int copyin(const user_addr_t address, void *destination, size_t length)
{
    ++calls;
    if (calls != 1 || address != expected_address || !destination || length != 4) {
        bad_call = 1;
        return EFAULT;
    }
    unsigned count = partial_copy ? 2 : 4;
    for (unsigned i = 0; i < count; ++i)
        ((unsigned char *)destination)[i] = (unsigned char)(supplied_word >> (8*i));
    return copy_error;
}

static arm_saved_state_t user_state(void)
{
    arm_saved_state_t state;
    memset(&state, 0xa5, sizeof(state));
    state.ash.flavor = ARM_SAVED_STATE64;
    state.ash.count = ARM_SAVED_STATE64_COUNT;
    state.ss_64.pc = UINT64_C(0xab00000000001000);
    state.ss_64.cpsr = 0xa0000000U;
    state.ss_64.lr = UINT64_C(0xcdef123456789abc);
    return state;
}

static int zero_descriptor(const struct n10_auth_branch *branch)
{
    return branch->kind == 0 && branch->key == 0 && branch->target_register == 0 &&
        branch->modifier_register == 0 && branch->modifier_kind == 0;
}

static int check(const arm_saved_state_t *state, uint32_t word, int error, int partial,
                 enum n10_user_branch_status status, enum n10_user_fetch_status fetched,
                 unsigned expected_calls)
{
    unsigned char before[sizeof(*state)];
    memcpy(before, state, sizeof(before));
    expected_address = state->ss_64.pc;
    supplied_word = word; copy_error = error; partial_copy = partial;
    calls = bad_call = 0;
    struct n10_user_branch_decode result = n10_decode_user_auth_branch(state);
    ++cases;
    if (result.status != status || result.fetch.status != fetched ||
        result.fetch.copy_error != error || result.fetch.word != (fetched == N10_USER_FETCH_OK ? word : 0) ||
        calls != expected_calls || bad_call || memcmp(before, state, sizeof(before)) != 0)
        return 0;
    if (status == N10_USER_BRANCH_DECODED)
        return result.branch.kind == N10_CALL && result.branch.key == N10_KEY_IA &&
            result.branch.target_register == 17 && result.branch.modifier_register == 9 &&
            result.branch.modifier_kind == N10_MOD_REGISTER;
    return zero_descriptor(&result.branch);
}

int main(void)
{
    const uint32_t blraa = 0xd73f0800U | (17U << 5) | 9U;
    /* Synthetic reserved hint BRK, using the existing hint_sites.h immediate. */
    const uint32_t hint_brk = 0xd4200000U | (0x4e10U << 5);
    arm_saved_state_t state = user_state();
    if (!check(&state, blraa, 0, 0, N10_USER_BRANCH_DECODED, N10_USER_FETCH_OK, 1))
        return 1;
    if (!check(&state, blraa, EFAULT, 1, N10_USER_BRANCH_FETCH_FAILED, N10_USER_FETCH_COPY_ERROR, 1))
        return 2;
    if (!check(&state, hint_brk, 0, 0, N10_USER_BRANCH_UNSUPPORTED, N10_USER_FETCH_OK, 1))
        return 3;
    state.ss_64.cpsr |= PSR64_MODE_EL1;
    if (!check(&state, blraa, 0, 0, N10_USER_BRANCH_FETCH_FAILED, N10_USER_FETCH_BAD_STATE, 0))
        return 4;
    printf("v165 user fetch to auth-branch decode: PASS (%u cases)\n", cases);
    return 0;
}
