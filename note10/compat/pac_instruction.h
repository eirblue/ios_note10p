#ifndef NOTE10_PAC_INSTRUCTION_H
#define NOTE10_PAC_INSTRUCTION_H
#include "soft_pac.h"
enum n10_pac_operation { N10_PAC_SIGN, N10_PAC_AUTH, N10_PAC_STRIP };
struct n10_pac_instruction {
    enum n10_pac_operation operation;
    unsigned key, destination;
    enum n10_modifier_kind modifier_kind;
    unsigned modifier_register, hint_encoding;
};
enum n10_pac_step_result {
    N10_PACSTEP_OK, N10_PACSTEP_UNSUPPORTED, N10_PACSTEP_BAD_CONTEXT,
    N10_PACSTEP_MISSING_KEY, N10_PACSTEP_OPERATION_FAILED
};
int n10_decode_pac(uint32_t word, struct n10_pac_instruction *out);
/* Explicit register-state model, not a trap handler. Hint encodings do not trap
 * on CPUs without PAuth; no interception/instrumentation strategy is included.
 * Failure leaves state unchanged. AUT failure uses the strict software model,
 * not architectural poison-pointer/FPAC behavior. PSTATE/BTI effects are absent.
 */
enum n10_pac_step_result n10_step_pac(uint32_t word, struct n10_user_state *state,
                                     const struct n10_fixup_pac_context *context);
#endif
