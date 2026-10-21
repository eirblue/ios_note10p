#include "auth_branch.h"
#include <stdio.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr, "failed line %d: %s\n", __LINE__, #x); return 1; } } while (0)

/* Test-only oracle callback. This is not a production PAC backend. */
struct mock { unsigned calls; enum n10_auth_key key; uint64_t pointer, modifier, target; int ok; };
static int mock_auth(void *opaque, enum n10_auth_key key, uint64_t ptr, uint64_t mod, uint64_t *target)
{
    struct mock *m = opaque;
    ++m->calls; m->key = key; m->pointer = ptr; m->modifier = mod;
    *target = m->target;
    return m->ok;
}

int main(int argc, char **argv)
{
    CHECK(argc == 2);
    FILE *f = fopen(argv[1], "rb");
    CHECK(f != NULL);
    unsigned records = 0;
    unsigned char buf[12];
    size_t bytes;
    while ((bytes = fread(buf, 1, sizeof(buf), f)) != 0) {
        CHECK(bytes == sizeof(buf));
        uint32_t word = (uint32_t)buf[0] | (uint32_t)buf[1] << 8 | (uint32_t)buf[2] << 16 | (uint32_t)buf[3] << 24;
        struct n10_auth_branch before = {N10_RETURN, N10_KEY_IB, 7, 8, N10_MOD_SP};
        struct n10_auth_branch d = before;
        int got = n10_decode_auth_branch(word, &d);
        CHECK(got == buf[4]);
        if (got) {
            CHECK((unsigned)d.kind == buf[5]); CHECK((unsigned)d.key == buf[6]);
            CHECK(d.target_register == buf[7]); CHECK(d.modifier_register == buf[8]);
            CHECK((unsigned)d.modifier_kind == buf[9]);
        } else {
            CHECK(memcmp(&d, &before, sizeof(d)) == 0);
        }
        ++records;
    }
    CHECK(!ferror(f)); CHECK(fclose(f) == 0); CHECK(records > 20000);
    CHECK(n10_decode_auth_branch(0xd65f0bffU, NULL) == 0);
    struct n10_user_state s = {{0}, 0x8000, 0x1000}, saved;
    struct mock m = {0, N10_KEY_IA, 0, 0, 0x4000, 1};
    s.x[4] = 0xaabb; s.x[3] = 0x1234; s.x[30] = 0x9000;
    saved = s;
    CHECK(n10_step_auth_branch(0xd71f0883U, &s, NULL, NULL) == N10_STEP_NEEDS_AUTH);
    CHECK(memcmp(&s, &saved, sizeof(s)) == 0);
    m.ok = 0;
    CHECK(n10_step_auth_branch(0xd73f0883U, &s, mock_auth, &m) == N10_STEP_AUTH_FAILED);
    CHECK(memcmp(&s, &saved, sizeof(s)) == 0);
    m.ok = 1; m.target = 0x4001;
    CHECK(n10_step_auth_branch(0xd73f0883U, &s, mock_auth, &m) == N10_STEP_BAD_TARGET);
    CHECK(memcmp(&s, &saved, sizeof(s)) == 0);
    m.target = 0x4000;
    CHECK(n10_step_auth_branch(0xd73f0bdeU, &s, mock_auth, &m) == N10_STEP_OK); /* blraa x30,x30 */
    CHECK(m.pointer == 0x9000 && m.modifier == 0x9000 && m.key == N10_KEY_IA);
    CHECK(s.x[30] == 0x1004 && s.pc == 0x4000);
    s = saved;
    CHECK(n10_step_auth_branch(0xd71f0bffU, &s, mock_auth, &m) == N10_STEP_OK); /* braa xzr,sp */
    CHECK(m.pointer == 0 && m.modifier == saved.sp);
    s = saved;
    CHECK(n10_step_auth_branch(0xd63f089fU, &s, mock_auth, &m) == N10_STEP_OK); /* blraaz x4 */
    CHECK(m.modifier == 0 && m.pointer == saved.x[4] && s.x[30] == 0x1004);
    s = saved;
    CHECK(n10_step_auth_branch(0xd65f0fffU, &s, mock_auth, &m) == N10_STEP_OK); /* retab */
    CHECK(m.key == N10_KEY_IB && m.pointer == saved.x[30] && m.modifier == saved.sp);
    CHECK(s.x[30] == saved.x[30] && s.sp == saved.sp && s.pc == m.target);
    s = saved;
    CHECK(n10_step_auth_branch(0xd65f03c0U, &s, mock_auth, &m) == N10_STEP_UNSUPPORTED); /* ordinary ret */
    CHECK(memcmp(&s, &saved, sizeof(s)) == 0);
    s.pc = 0x1001; saved = s;
    CHECK(n10_step_auth_branch(0xd65f0bffU, &s, mock_auth, &m) == N10_STEP_BAD_CONTEXT);
    CHECK(memcmp(&s, &saved, sizeof(s)) == 0);
    s.pc = UINT64_MAX - 3;
    CHECK(n10_step_auth_branch(0xd65f0bffU, &s, mock_auth, &m) == N10_STEP_BAD_CONTEXT);
    CHECK(n10_step_auth_branch(0xd65f0bffU, NULL, mock_auth, &m) == N10_STEP_BAD_CONTEXT);
    printf("{\"oracle_records\":%u,\"assertions\":%u,\"passed\":true}\n", records, checks);
    return 0;
}
