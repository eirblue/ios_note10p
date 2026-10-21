#include "auth_branch.h"

int n10_decode_auth_branch(uint32_t word, struct n10_auth_branch *out)
{
    if (!out)
        return 0;
    struct n10_auth_branch d = {N10_BRANCH, N10_KEY_IA, (word >> 5) & 31, word & 31, N10_MOD_REGISTER};
    if (word == 0xd65f0bffU || word == 0xd65f0fffU) {
        d.kind = N10_RETURN;
        d.key = word == 0xd65f0bffU ? N10_KEY_IA : N10_KEY_IB;
        d.target_register = 30;
        d.modifier_register = 31;
        d.modifier_kind = N10_MOD_SP;
    } else {
        uint32_t reg = word & 0xfffffc00U;
        uint32_t zero = word & 0xfffffc1fU;
        switch (reg) {
        case 0xd71f0800U: d.kind = N10_BRANCH; d.key = N10_KEY_IA; break;
        case 0xd71f0c00U: d.kind = N10_BRANCH; d.key = N10_KEY_IB; break;
        case 0xd73f0800U: d.kind = N10_CALL; d.key = N10_KEY_IA; break;
        case 0xd73f0c00U: d.kind = N10_CALL; d.key = N10_KEY_IB; break;
        default:
            switch (zero) {
            case 0xd61f081fU: d.kind = N10_BRANCH; d.key = N10_KEY_IA; break;
            case 0xd61f0c1fU: d.kind = N10_BRANCH; d.key = N10_KEY_IB; break;
            case 0xd63f081fU: d.kind = N10_CALL; d.key = N10_KEY_IA; break;
            case 0xd63f0c1fU: d.kind = N10_CALL; d.key = N10_KEY_IB; break;
            default: return 0;
            }
            d.modifier_kind = N10_MOD_ZERO;
            break;
        }
        if (d.modifier_kind != N10_MOD_ZERO && d.modifier_register == 31)
            d.modifier_kind = N10_MOD_SP;
    }
    *out = d;
    return 1;
}

enum n10_step_result n10_step_auth_branch(uint32_t word,
                                         struct n10_user_state *state,
                                         n10_authenticate_fn authenticate,
                                         void *context)
{
    struct n10_auth_branch d;
    if (!n10_decode_auth_branch(word, &d))
        return N10_STEP_UNSUPPORTED;
    if (!state || (state->pc & 3) || state->pc > UINT64_MAX - 4)
        return N10_STEP_BAD_CONTEXT;
    if (!authenticate)
        return N10_STEP_NEEDS_AUTH;
    uint64_t pointer = d.target_register == 31 ? 0 : state->x[d.target_register];
    uint64_t modifier = 0, target = 0;
    if (d.modifier_kind == N10_MOD_SP)
        modifier = state->sp;
    else if (d.modifier_kind == N10_MOD_REGISTER)
        modifier = state->x[d.modifier_register];
    if (authenticate(context, d.key, pointer, modifier, &target) != 1)
        return N10_STEP_AUTH_FAILED;
    if (target & 3)
        return N10_STEP_BAD_TARGET;
    /* Read pointer/modifier before changing LR, including register aliases. */
    if (d.kind == N10_CALL)
        state->x[30] = state->pc + 4;
    state->pc = target;
    return N10_STEP_OK;
}
