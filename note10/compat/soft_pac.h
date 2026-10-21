#ifndef NOTE10_SOFT_PAC_H
#define NOTE10_SOFT_PAC_H
#include "qarma.h"
#include "auth_branch.h"
/* Restricted lower-address-range software model. Caller must choose a validated
 * profile; this is NOT an Apple ARM64e_X1 profile or full AddPAC/AUT emulation.
 * No upper range, PAC2/EPAC, MTE, poisoned failure pointer or exception delivery.
 */
struct n10_pac_profile { unsigned va_bits, top_byte_ignore, rounds; };
enum n10_pac_result { N10_PAC_OK, N10_PAC_BAD_INPUT, N10_PAC_BAD_POINTER, N10_PAC_AUTH_FAILED };
enum n10_pac_result n10_pac_sign(const struct n10_pac_profile *profile,
                                const struct n10_pac_key *key, uint64_t pointer,
                                uint64_t modifier, uint64_t *out);
enum n10_pac_result n10_pac_auth(const struct n10_pac_profile *profile,
                                const struct n10_pac_key *key, uint64_t pointer,
                                uint64_t modifier, uint64_t *out);
enum n10_pac_result n10_pac_strip(const struct n10_pac_profile *profile,
                                 uint64_t pointer, uint64_t *out);
/* Keys are supplied by caller; no production key generation/storage is included. */
struct n10_branch_pac_context {
    struct n10_pac_profile profile;
    struct n10_pac_key keys[2];
    unsigned present_mask;
};
int n10_software_auth_branch(void *context, enum n10_auth_key key,
                              uint64_t pointer, uint64_t modifier, uint64_t *target);
typedef int (*n10_blend_modifier_fn)(void *context, uint64_t slot,
                                    uint16_t diversity, uint64_t *modifier);
struct n10_fixup_pac_context {
    struct n10_pac_profile profiles[2]; /* instruction, data */
    struct n10_pac_key keys[4]; /* IA, IB, DA, DB */
    unsigned present_mask;
    n10_blend_modifier_fn blend;
    void *blend_context;
};
/* Address-diverse pointers require a caller-provided, validated blend rule.
 * No Apple ARM64e_X1 blend algorithm is guessed here. Missing rule rejects sign.
 */
int n10_software_sign_fixup(void *context, uint8_t key, uint16_t diversity,
                             uint8_t address_diversity, uint64_t slot,
                             uint64_t pointer, uint64_t *out);
#endif
