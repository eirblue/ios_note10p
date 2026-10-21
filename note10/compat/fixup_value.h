#ifndef NOTE10_FIXUP_VALUE_H
#define NOTE10_FIXUP_VALUE_H
#include "fixup24.h"
/* Signing backend must implement the process/ABI's signing and modifier rules.
 * Passing metadata separately avoids silently guessing address-diversity mixing.
 */
typedef int (*n10_sign_fixup_fn)(void *context, uint8_t key, uint16_t diversity,
                                uint8_t address_diversity, uint64_t slot_address,
                                uint64_t pointer, uint64_t *signed_pointer);
enum n10_value_result {
    N10_VALUE_OK, N10_VALUE_BAD_INPUT, N10_VALUE_ENCODING,
    N10_VALUE_BAD_ORDINAL, N10_VALUE_OVERFLOW, N10_VALUE_NEEDS_SIGN,
    N10_VALUE_SIGN_FAILED
};
/* Pure value computation, no writes to an image. bind_targets must already
 * contain resolved symbol addresses including import-table addends. Chain-word
 * addends are applied here. Authenticated null binds remain null, as in dyld.
 * *out is unchanged on failure. Callbacks must not alias/mutate *out or inputs.
 */
enum n10_value_result n10_fixup24_value(uint64_t raw, uint64_t image_base,
                                       uint64_t slot_address,
                                       const uint64_t *bind_targets, size_t bind_count,
                                       n10_sign_fixup_fn sign, void *context,
                                       uint64_t *out);
#endif
