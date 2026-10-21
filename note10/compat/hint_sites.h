#ifndef NOTE10_HINT_SITES_H
#define NOTE10_HINT_SITES_H
#include <stddef.h>
#include "pac_instruction.h"
#define N10_HINT_BRK (0xd4200000U | (0x4e10U << 5))
struct n10_hint_site { uint64_t address; uint32_t original_word; };
struct n10_hint_table {
    const struct n10_hint_site *sites;
    size_t count;
    uint64_t slide;
};
/* Caller owns a trusted, immutable table per mapped image/process. Validate
 * after assigning slide and before publishing it. No user memory is fetched.
 * Positive unsigned slides only; no ASLR, lifetime or mapping policy is supplied.
 */
int n10_hint_table_validate(const struct n10_hint_table *table);
enum n10_hint_result {
    N10_HINT_OK, N10_HINT_BAD_CONTEXT, N10_HINT_NOT_REGISTERED,
    N10_HINT_WORD_MISMATCH, N10_HINT_MODEL_FAILED
};
/* fetched_word must come from a fault-safe instruction fetch at saved PC in
 * the owning address space. Caller has already validated table immutability.
 * A matching BRK immediate alone is never sufficient to dispatch.
 */
enum n10_hint_result n10_hint_dispatch(const struct n10_hint_table *table,
    uint32_t fetched_word, struct n10_user_state *state,
    const struct n10_fixup_pac_context *context);
#endif
