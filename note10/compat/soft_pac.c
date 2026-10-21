#include "soft_pac.h"

static int masks(const struct n10_pac_profile *p, uint64_t *pac_mask, uint64_t *address_mask)
{
    if (!p || p->va_bits < 32 || p->va_bits > 48 || p->top_byte_ignore > 1 ||
        (p->rounds != 3 && p->rounds != 5))
        return 0;
    uint64_t low = (UINT64_C(1) << p->va_bits) - 1;
    uint64_t top = p->top_byte_ignore ? UINT64_C(0xff00000000000000) : 0;
    *address_mask = low | top;
    *pac_mask = ~(low | top | (UINT64_C(1) << 55));
    return 1;
}

enum n10_pac_result n10_pac_sign(const struct n10_pac_profile *profile,
                                const struct n10_pac_key *key, uint64_t pointer,
                                uint64_t modifier, uint64_t *out)
{
    uint64_t pac_mask, address_mask, mac = 0;
    if (!key || !out || !masks(profile, &pac_mask, &address_mask))
        return N10_PAC_BAD_INPUT;
    if (pointer & ~address_mask)
        return N10_PAC_BAD_POINTER;
    if (!n10_qarma(pointer, modifier, key, profile->rounds, &mac))
        return N10_PAC_BAD_INPUT;
    *out = pointer | (mac & pac_mask);
    return N10_PAC_OK;
}

enum n10_pac_result n10_pac_auth(const struct n10_pac_profile *profile,
                                const struct n10_pac_key *key, uint64_t pointer,
                                uint64_t modifier, uint64_t *out)
{
    uint64_t pac_mask, address_mask, mac = 0;
    if (!key || !out || !masks(profile, &pac_mask, &address_mask))
        return N10_PAC_BAD_INPUT;
    if (pointer & (UINT64_C(1) << 55))
        return N10_PAC_BAD_POINTER;
    uint64_t original = pointer & address_mask;
    if (!n10_qarma(original, modifier, key, profile->rounds, &mac))
        return N10_PAC_BAD_INPUT;
    if ((pointer ^ mac) & pac_mask)
        return N10_PAC_AUTH_FAILED;
    *out = original;
    return N10_PAC_OK;
}

enum n10_pac_result n10_pac_strip(const struct n10_pac_profile *profile,
                                 uint64_t pointer, uint64_t *out)
{
    uint64_t pac_mask, address_mask;
    if (!out || !masks(profile, &pac_mask, &address_mask))
        return N10_PAC_BAD_INPUT;
    if (pointer & (UINT64_C(1) << 55))
        return N10_PAC_BAD_POINTER;
    *out = pointer & address_mask;
    return N10_PAC_OK;
}

int n10_software_auth_branch(void *context, enum n10_auth_key key,
                              uint64_t pointer, uint64_t modifier, uint64_t *target)
{
    struct n10_branch_pac_context *c = context;
    if (!c || (key != N10_KEY_IA && key != N10_KEY_IB) || !(c->present_mask & (1U << key)))
        return 0;
    return n10_pac_auth(&c->profile, &c->keys[key], pointer, modifier, target) == N10_PAC_OK;
}

int n10_software_sign_fixup(void *context, uint8_t key, uint16_t diversity,
                             uint8_t address_diversity, uint64_t slot,
                             uint64_t pointer, uint64_t *out)
{
    struct n10_fixup_pac_context *c = context;
    if (!c || key > 3 || address_diversity > 1 || !(c->present_mask & (1U << key)))
        return 0;
    uint64_t modifier = diversity;
    if (address_diversity && (!c->blend || c->blend(c->blend_context, slot, diversity, &modifier) != 1))
        return 0;
    return n10_pac_sign(&c->profiles[key >= 2], &c->keys[key], pointer, modifier, out) == N10_PAC_OK;
}
