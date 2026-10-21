#include "fixup_value.h"

enum n10_value_result n10_fixup24_value(uint64_t raw, uint64_t image_base,
                                       uint64_t slot_address,
                                       const uint64_t *bind_targets, size_t bind_count,
                                       n10_sign_fixup_fn sign, void *context,
                                       uint64_t *out)
{
    if (!out)
        return N10_VALUE_BAD_INPUT;
    struct n10_fixup24 d;
    if (!n10_decode_fixup24(raw, &d))
        return N10_VALUE_ENCODING;
    uint64_t value;
    if (d.bind) {
        if (d.ordinal >= bind_count)
            return N10_VALUE_BAD_ORDINAL;
        if (!bind_targets)
            return N10_VALUE_BAD_INPUT;
        value = bind_targets[d.ordinal];
        if (!d.authenticated) {
            if (d.addend >= 0) {
                if (value > UINT64_MAX - (uint64_t)d.addend)
                    return N10_VALUE_OVERFLOW;
                value += (uint64_t)d.addend;
            } else {
                uint64_t magnitude = (uint64_t)(-(int64_t)d.addend);
                if (value < magnitude)
                    return N10_VALUE_OVERFLOW;
                value -= magnitude;
            }
        }
    } else {
        uint64_t target = d.target | ((uint64_t)d.high8 << 56);
        if (image_base > UINT64_MAX - target)
            return N10_VALUE_OVERFLOW;
        value = image_base + target;
    }
    if (d.authenticated && !(d.bind && value == 0)) {
        if (!sign)
            return N10_VALUE_NEEDS_SIGN;
        uint64_t signed_value = 0;
        if (sign(context, d.key, d.diversity, d.address_diversity,
                 slot_address, value, &signed_value) != 1)
            return N10_VALUE_SIGN_FAILED;
        value = signed_value;
    }
    *out = value;
    return N10_VALUE_OK;
}
