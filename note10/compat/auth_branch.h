#ifndef NOTE10_AUTH_BRANCH_H
#define NOTE10_AUTH_BRANCH_H
#include <stdint.h>

enum n10_branch_kind { N10_BRANCH, N10_CALL, N10_RETURN };
enum n10_auth_key { N10_KEY_IA, N10_KEY_IB };
enum n10_modifier_kind { N10_MOD_REGISTER, N10_MOD_SP, N10_MOD_ZERO };
struct n10_auth_branch {
    enum n10_branch_kind kind;
    enum n10_auth_key key;
    unsigned target_register; /* 31 means XZR, not SP. */
    unsigned modifier_register;
    enum n10_modifier_kind modifier_kind;
};
struct n10_user_state { uint64_t x[31], sp, pc; };
/* The backend must authenticate the pointer with the correct process key and
 * address rules. Return 1 only on verified success; no permissive backend exists.
 * This module does not implement PAC cryptography, key management, or XNU traps.
 */
typedef int (*n10_authenticate_fn)(void *context, enum n10_auth_key key,
                                 uint64_t pointer, uint64_t modifier,
                                 uint64_t *verified_target);
enum n10_step_result {
    N10_STEP_OK, N10_STEP_UNSUPPORTED, N10_STEP_NEEDS_AUTH,
    N10_STEP_AUTH_FAILED, N10_STEP_BAD_CONTEXT, N10_STEP_BAD_TARGET
};
int n10_decode_auth_branch(uint32_t word, struct n10_auth_branch *out);
/* A narrow register/PC transition model, not a full architectural emulator.
 * State is unchanged on failure. PSTATE/BTYPE, BTI, faults and traps are external.
 */
enum n10_step_result n10_step_auth_branch(uint32_t word,
                                         struct n10_user_state *state,
                                         n10_authenticate_fn authenticate,
                                         void *context);
#endif
