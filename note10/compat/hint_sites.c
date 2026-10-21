#include "hint_sites.h"
int n10_hint_table_validate(const struct n10_hint_table *t)
{
    if (!t || (t->count && !t->sites) || (t->slide & 3)) return 0;
    for (size_t i = 0; i < t->count; ++i) {
        const struct n10_hint_site *s = &t->sites[i];
        struct n10_pac_instruction d;
        if ((s->address & 3) || s->address > UINT64_MAX - t->slide ||
            s->address + t->slide > UINT64_MAX - 4 ||
            (i && s->address <= t->sites[i-1].address) ||
            !n10_decode_pac(s->original_word, &d) || !d.hint_encoding) return 0;
    }
    return 1;
}
enum n10_hint_result n10_hint_dispatch(const struct n10_hint_table *t,
    uint32_t word, struct n10_user_state *state,
    const struct n10_fixup_pac_context *context)
{
    if (!t || (t->count && !t->sites) || !state || !context ||
        (t->slide & 3) || (state->pc & 3) || state->pc < t->slide ||
        state->pc > UINT64_MAX - 4) return N10_HINT_BAD_CONTEXT;
    uint64_t address = state->pc - t->slide;
    size_t lo = 0, hi = t->count;
    while (lo < hi) {
        size_t mid = lo + (hi - lo) / 2;
        if (t->sites[mid].address < address) lo = mid + 1;
        else hi = mid;
    }
    if (lo == t->count || t->sites[lo].address != address) return N10_HINT_NOT_REGISTERED;
    if (word != N10_HINT_BRK) return N10_HINT_WORD_MISMATCH;
    struct n10_pac_instruction d;
    if (!n10_decode_pac(t->sites[lo].original_word, &d) || !d.hint_encoding)
        return N10_HINT_BAD_CONTEXT;
    if (n10_step_pac(t->sites[lo].original_word, state, context) != N10_PACSTEP_OK)
        return N10_HINT_MODEL_FAILED;
    return N10_HINT_OK;
}
