#include "soft_pac.h"
#include "fixup_value.h"
#include <stdio.h>
#include <string.h>
static unsigned checks, roundtrips, tamper_checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); return 1; } } while (0)
static uint64_t random64(uint64_t *state)
{
    *state ^= *state << 13; *state ^= *state >> 7; *state ^= *state << 17; return *state;
}
int main(void)
{
    struct n10_pac_key known = {0xec2802d4e0a488e9ULL, 0x84be85ce9804e94bULL};
    uint64_t result = 0;
    CHECK(n10_qarma(0xfb623599da6e8127ULL, 0x477d469dec0b8762ULL, &known, 5, &result));
    CHECK(result == 0xc003b93999b33765ULL); /* Published sigma2 known answer. */
    result = 123;
    CHECK(!n10_qarma(0, 0, &known, 4, &result) && result == 123);
    CHECK(!n10_qarma(0, 0, NULL, 5, &result) && result == 123);
    CHECK(!n10_qarma(0, 0, &known, 5, NULL));
    uint64_t rng = 976;
    for (unsigned rounds = 3; rounds <= 5; rounds += 2)
    for (unsigned va = 39; va <= 48; va += 9)
    for (unsigned tbi = 0; tbi <= 1; ++tbi) {
        struct n10_pac_profile p = {va, tbi, rounds};
        uint64_t low = (UINT64_C(1) << va) - 1;
        uint64_t tag_mask = tbi ? 0xff00000000000000ULL : 0;
        uint64_t pac_mask = ~(low | tag_mask | (1ULL << 55));
        for (unsigned i = 0; i < 256; ++i) {
            struct n10_pac_key key = {random64(&rng), random64(&rng)};
            uint64_t ptr = random64(&rng) & low;
            ptr |= random64(&rng) & tag_mask;
            uint64_t mod = random64(&rng), signed_ptr = 0, plain = 0;
            CHECK(n10_pac_sign(&p, &key, ptr, mod, &signed_ptr) == N10_PAC_OK);
            CHECK((signed_ptr & (low | tag_mask)) == ptr);
            CHECK(n10_pac_auth(&p, &key, signed_ptr, mod, &plain) == N10_PAC_OK && plain == ptr);
            ++roundtrips;
            /* Flipping a signature bit must fail without changing the address. */
            for (unsigned bit = 0; bit < 64; ++bit) if ((pac_mask >> bit) & 1) {
                plain = 0xbeef;
                CHECK(n10_pac_auth(&p, &key, signed_ptr ^ (1ULL << bit), mod, &plain) == N10_PAC_AUTH_FAILED && plain == 0xbeef);
                ++tamper_checks;
            }
        }
    }
    struct n10_branch_pac_context ctx = {{39, 0, 5}, {{1, 2}, {3, 4}}, 3};
    struct n10_user_state state = {{0}, 0x8000, 0x1000}, original;
    uint64_t signed_target;
    CHECK(n10_pac_sign(&ctx.profile, &ctx.keys[0], 0x4000, 0x7777, &signed_target) == N10_PAC_OK);
    state.x[4] = signed_target; state.x[3] = 0x7777;
    CHECK(n10_step_auth_branch(0xd73f0883U, &state, n10_software_auth_branch, &ctx) == N10_STEP_OK);
    CHECK(state.pc == 0x4000 && state.x[30] == 0x1004);
    state.pc = 0x1000; state.x[4] ^= 1ULL << 40; original = state;
    CHECK(n10_step_auth_branch(0xd73f0883U, &state, n10_software_auth_branch, &ctx) == N10_STEP_AUTH_FAILED);
    CHECK(memcmp(&state, &original, sizeof(state)) == 0);
    struct n10_fixup_pac_context fix = {{{39, 0, 5}, {48, 1, 5}}, {{1, 2}, {3, 4}, {5, 6}, {7, 8}}, 15, NULL, NULL};
    uint64_t raw_fixup = (1ULL << 63) | (0x7777ULL << 32) | 0x4000;
    result = 123;
    CHECK(n10_fixup24_value(raw_fixup, 0x100000000ULL, 0x100002000ULL, NULL, 0, n10_software_sign_fixup, &fix, &result) == N10_VALUE_OK);
    ctx.present_mask = 3; state.pc = 0x1000; state.x[4] = result; state.x[3] = 0x7777;
    CHECK(n10_step_auth_branch(0xd73f0883U, &state, n10_software_auth_branch, &ctx) == N10_STEP_OK);
    CHECK(state.pc == 0x100004000ULL && state.x[30] == 0x1004);
    result = 123;
    CHECK(n10_fixup24_value(raw_fixup | (1ULL << 48), 0x100000000ULL, 0x100002000ULL, NULL, 0, n10_software_sign_fixup, &fix, &result) == N10_VALUE_SIGN_FAILED && result == 123);
    fix.present_mask = 0;
    CHECK(n10_fixup24_value(raw_fixup, 0x100000000ULL, 0x100002000ULL, NULL, 0, n10_software_sign_fixup, &fix, &result) == N10_VALUE_SIGN_FAILED && result == 123);
    CHECK(!n10_software_sign_fixup(NULL, 0, 0, 0, 0, 0, &result));
    CHECK(!n10_software_sign_fixup(&fix, 4, 0, 0, 0, 0, &result));
    ctx.present_mask = 0;
    CHECK(n10_step_auth_branch(0xd73f0883U, &state, n10_software_auth_branch, &ctx) == N10_STEP_AUTH_FAILED);
    struct n10_pac_profile invalid = {31, 0, 5}; result = 123;
    CHECK(n10_pac_sign(&invalid, &known, 0, 0, &result) == N10_PAC_BAD_INPUT && result == 123);
    invalid.va_bits = 49; CHECK(n10_pac_auth(&invalid, &known, 0, 0, &result) == N10_PAC_BAD_INPUT);
    invalid.va_bits = 39; invalid.top_byte_ignore = 2;
    CHECK(n10_pac_auth(&invalid, &known, 0, 0, &result) == N10_PAC_BAD_INPUT);
    CHECK(n10_pac_sign(&ctx.profile, &known, 1ULL << 55, 0, &result) == N10_PAC_BAD_POINTER);
    CHECK(n10_pac_auth(&ctx.profile, &known, 1ULL << 55, 0, &result) == N10_PAC_BAD_POINTER);
    printf("{\"known_answer\":\"QARMA64_5_sigma2\",\"roundtrips\":%u,\"signature_bit_tamper_checks\":%u,\"assertions\":%u,\"passed\":true}\n", roundtrips, tamper_checks, checks);
    return 0;
}
