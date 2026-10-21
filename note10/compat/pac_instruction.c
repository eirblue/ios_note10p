#include "pac_instruction.h"

int n10_decode_pac(uint32_t word, struct n10_pac_instruction *out)
{
    if (!out) return 0;
    struct n10_pac_instruction d = {N10_PAC_SIGN, 0, word & 31, N10_MOD_REGISTER, (word >> 5) & 31, 0};
    if ((word & 0xffffe000U) == 0xdac10000U) {
        unsigned group = (word >> 10) & 7;
        d.operation = group < 4 ? N10_PAC_SIGN : N10_PAC_AUTH;
        d.key = group & 3;
        if (d.modifier_register == 31) d.modifier_kind = N10_MOD_SP;
    } else {
        uint32_t base = word & 0xffffffe0U;
        static const uint32_t zero_forms[8] = {
            0xdac123e0U, 0xdac127e0U, 0xdac12be0U, 0xdac12fe0U,
            0xdac133e0U, 0xdac137e0U, 0xdac13be0U, 0xdac13fe0U
        };
        unsigned i;
        for (i = 0; i < 8 && base != zero_forms[i]; ++i) {}
        if (i < 8) {
            d.operation = i < 4 ? N10_PAC_SIGN : N10_PAC_AUTH;
            d.key = i & 3; d.modifier_kind = N10_MOD_ZERO; d.modifier_register = 31;
        } else if (base == 0xdac143e0U || base == 0xdac147e0U) {
            d.operation = N10_PAC_STRIP; d.key = base == 0xdac143e0U ? 0 : 2;
            d.modifier_kind = N10_MOD_ZERO; d.modifier_register = 31;
        } else {
            struct hint { uint32_t word; unsigned op, key, rd, mod, rn; };
            static const struct hint hints[] = {
                {0xd503211fU,0,0,17,0,16}, {0xd503215fU,0,1,17,0,16},
                {0xd503219fU,1,0,17,0,16}, {0xd50321dfU,1,1,17,0,16},
                {0xd503231fU,0,0,30,2,31}, {0xd503233fU,0,0,30,1,31},
                {0xd503235fU,0,1,30,2,31}, {0xd503237fU,0,1,30,1,31},
                {0xd503239fU,1,0,30,2,31}, {0xd50323bfU,1,0,30,1,31},
                {0xd50323dfU,1,1,30,2,31}, {0xd50323ffU,1,1,30,1,31},
                {0xd50320ffU,2,0,30,2,31}
            };
            for (i = 0; i < sizeof(hints) / sizeof(hints[0]) && word != hints[i].word; ++i) {}
            if (i == sizeof(hints) / sizeof(hints[0])) return 0;
            d.operation = (enum n10_pac_operation)hints[i].op;
            d.key = hints[i].key; d.destination = hints[i].rd;
            d.modifier_kind = (enum n10_modifier_kind)hints[i].mod;
            d.modifier_register = hints[i].rn; d.hint_encoding = 1;
        }
    }
    *out = d;
    return 1;
}

enum n10_pac_step_result n10_step_pac(uint32_t word, struct n10_user_state *state,
                                     const struct n10_fixup_pac_context *context)
{
    struct n10_pac_instruction d;
    if (!n10_decode_pac(word, &d)) return N10_PACSTEP_UNSUPPORTED;
    if (!state || !context || (state->pc & 3) || state->pc > UINT64_MAX - 4)
        return N10_PACSTEP_BAD_CONTEXT;
    if (d.operation != N10_PAC_STRIP && !(context->present_mask & (1U << d.key)))
        return N10_PACSTEP_MISSING_KEY;
    uint64_t pointer = d.destination == 31 ? 0 : state->x[d.destination];
    uint64_t modifier = d.modifier_kind == N10_MOD_SP ? state->sp :
        (d.modifier_kind == N10_MOD_ZERO ? 0 : state->x[d.modifier_register]);
    uint64_t result = 0;
    const struct n10_pac_profile *p = &context->profiles[d.key >= 2];
    enum n10_pac_result status;
    if (d.operation == N10_PAC_STRIP) status = n10_pac_strip(p, pointer, &result);
    else if (d.operation == N10_PAC_SIGN) status = n10_pac_sign(p, &context->keys[d.key], pointer, modifier, &result);
    else status = n10_pac_auth(p, &context->keys[d.key], pointer, modifier, &result);
    if (status != N10_PAC_OK) return N10_PACSTEP_OPERATION_FAILED;
    if (d.destination != 31) state->x[d.destination] = result;
    state->pc += 4;
    return N10_PACSTEP_OK;
}
