/* SPDX-License-Identifier: GPL-2.0-only */
/* Temporary comparison evidence and one bounded late 8-byte prefix sample. */
#ifndef N10_DATA_COMPARE_EVIDENCE_H
#define N10_DATA_COMPARE_EVIDENCE_H
#ifndef N10_COMPARE_CLEAR
#error "explicit evidence scratch clearing required"
#endif
#define N10_DATA_COMPARE_BODY_MAX 415u
struct n10_data_compare_evidence {
    unsigned char actual[32], expected[32];
    unsigned int evaluated, equal;
    unsigned int sampled, magic_match, prefix_zero;
};
_Static_assert(sizeof(struct n10_data_compare_evidence) == 84, "exact temporary comparison evidence");

static void n10_data_compare_capture(struct n10_data_compare_evidence *out,
    const unsigned char actual[32], const unsigned char expected[32], int comparison)
{
    memcpy(out->actual, actual, 32);
    memcpy(out->expected, expected, 32);
    out->equal = comparison == 0;
    out->evaluated = 1;
}

static void n10_data_input_probe(struct n10_data_compare_evidence *out,
    const unsigned char *input)
{
    unsigned char prefix[8];
    unsigned int i, any = 0;
    if (!out->evaluated) return;
    /* The caller has completed the existing hash and digest comparison.
     * Read only these 8 bytes; derive scalars from the local copy. */
    memcpy(prefix, input, sizeof(prefix));
    for (i = 0; i < sizeof(prefix); ++i) any |= prefix[i];
    out->magic_match = memcmp(prefix, "N10DATA1", sizeof(prefix)) == 0;
    out->prefix_zero = !any;
    out->sampled = 1;
    N10_COMPARE_CLEAR(prefix, sizeof(prefix));
}

static void n10_data_compare_clear(struct n10_data_compare_evidence *out)
{
    N10_COMPARE_CLEAR(out, sizeof(*out));
}

static int n10_data_compare_format(const struct n10_data_compare_evidence *out,
    char *frame, size_t capacity, char actual[65], char expected[65],
    const char *identity, const char *cycle, unsigned long long logical)
{
    static const char digits[] = "0123456789abcdef";
    unsigned int i;
    int count;
    for (i = 0; i < 32; ++i) {
        actual[2*i] = digits[out->actual[i] >> 4];
        actual[2*i+1] = digits[out->actual[i] & 15];
        expected[2*i] = digits[out->expected[i] >> 4];
        expected[2*i+1] = digits[out->expected[i] & 15];
    }
    actual[64] = 0; expected[64] = 0;
    count = snprintf(frame, capacity,
        "id=%s cycle=%s kind=compare source=image-slot-logical-v2 phase=carrier_integrity state=%s logical=%llu actual=%s expected=%s equal=%s sampled=%u magic_match=%u prefix_zero=%u ownership=0 executed=0",
        identity, cycle, out->evaluated ? "compared" : "unavailable", logical,
        actual, expected, out->evaluated ? (out->equal ? "1" : "0") : "na",
        out->sampled, out->magic_match, out->prefix_zero);
    N10_COMPARE_CLEAR(actual, 65);
    N10_COMPARE_CLEAR(expected, 65);
    if (count < 1 || (size_t)count >= capacity || (unsigned int)count > N10_DATA_COMPARE_BODY_MAX) {
        N10_COMPARE_CLEAR(frame, capacity);
        return 0;
    }
    return count;
}
#endif
