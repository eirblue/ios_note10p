#include "pac_instruction.h"
#include <stdio.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); return 1; } } while (0)
int main(int argc, char **argv)
{
    CHECK(argc == 2);
    FILE *f = fopen(argv[1], "rb"); CHECK(f != NULL);
    unsigned records = 0; unsigned char b[12]; size_t bytes;
    while ((bytes = fread(b, 1, sizeof(b), f)) != 0) {
        CHECK(bytes == sizeof(b));
        uint32_t word = (uint32_t)b[0] | (uint32_t)b[1] << 8 | (uint32_t)b[2] << 16 | (uint32_t)b[3] << 24;
        struct n10_pac_instruction d, before;
        memset(&before, 0, sizeof(before)); memcpy(&d, &before, sizeof(d));
        CHECK(n10_decode_pac(word, &d) == b[4]);
        if (b[4]) {
            CHECK((unsigned)d.operation == b[5]); CHECK(d.key == b[6]); CHECK(d.destination == b[7]);
            CHECK((unsigned)d.modifier_kind == b[8]); CHECK(d.modifier_register == b[9]); CHECK(d.hint_encoding == b[10]);
        } else CHECK(memcmp(&d, &before, sizeof(d)) == 0);
        ++records;
    }
    CHECK(!ferror(f)); CHECK(fclose(f) == 0); CHECK(records > 20000);
    struct n10_fixup_pac_context c = {{{39,0,5},{39,1,5}},{{1,2},{3,4},{5,6},{7,8}},15,NULL,NULL};
    struct n10_user_state s = {{0}, 0x8000, 0x1000}, before;
    for (unsigned key = 0; key < 4; ++key) {
        s.x[0] = 0x4000; s.x[1] = 0x7777;
        uint64_t pc = s.pc;
        CHECK(n10_step_pac(0xdac10020U | (key << 10), &s, &c) == N10_PACSTEP_OK);
        CHECK(n10_step_pac(0xdac11020U | (key << 10), &s, &c) == N10_PACSTEP_OK);
        CHECK(s.x[0] == 0x4000 && s.pc == pc + 8 && s.x[1] == 0x7777);
        s.x[0] = 0x5000;
        CHECK(n10_step_pac(0xdac123e0U | (key << 10), &s, &c) == N10_PACSTEP_OK);
        CHECK(n10_step_pac(0xdac133e0U | (key << 10), &s, &c) == N10_PACSTEP_OK && s.x[0] == 0x5000);
    }
    s.x[30] = 0x6000;
    CHECK(n10_step_pac(0xd503237fU, &s, &c) == N10_PACSTEP_OK); /* pacibsp model */
    CHECK(n10_step_pac(0xd50323ffU, &s, &c) == N10_PACSTEP_OK && s.x[30] == 0x6000);
    s.x[17] = 0x7000; s.x[16] = 0x8888;
    CHECK(n10_step_pac(0xd503211fU, &s, &c) == N10_PACSTEP_OK);
    CHECK(n10_step_pac(0xd503219fU, &s, &c) == N10_PACSTEP_OK && s.x[17] == 0x7000);
    s.x[0] = 0x4000;
    CHECK(n10_step_pac(0xdac103e0U, &s, &c) == N10_PACSTEP_OK); /* pacia x0,sp */
    CHECK(n10_step_pac(0xdac113e0U, &s, &c) == N10_PACSTEP_OK && s.x[0] == 0x4000);
    s.x[0] = 0x4000; uint64_t expected = 0;
    CHECK(n10_pac_sign(&c.profiles[0], &c.keys[0], 0x4000, 0x4000, &expected) == N10_PAC_OK);
    CHECK(n10_step_pac(0xdac10000U, &s, &c) == N10_PACSTEP_OK && s.x[0] == expected); /* alias */
    CHECK(n10_step_pac(0xdac143e0U, &s, &c) == N10_PACSTEP_OK && s.x[0] == 0x4000);
    s.x[30] = expected;
    CHECK(n10_step_pac(0xd50320ffU, &s, &c) == N10_PACSTEP_OK && s.x[30] == 0x4000);
    s.x[0] = expected ^ (1ULL << 40); s.x[1] = 0x4000; before = s;
    CHECK(n10_step_pac(0xdac11020U, &s, &c) == N10_PACSTEP_OPERATION_FAILED);
    CHECK(memcmp(&s, &before, sizeof(s)) == 0);
    c.present_mask = 0;
    CHECK(n10_step_pac(0xdac10020U, &s, &c) == N10_PACSTEP_MISSING_KEY && memcmp(&s, &before, sizeof(s)) == 0);
    CHECK(n10_step_pac(0xdac143e0U, &s, &c) == N10_PACSTEP_OK && s.x[0] == 0x4000); /* strip needs no key */
    c.present_mask = 15; s.x[0] = 0x4000; s.x[1] = 0; uint64_t lr = s.x[30], pc = s.pc;
    CHECK(n10_step_pac(0xdac1003fU, &s, &c) == N10_PACSTEP_OK && s.pc == pc + 4 && s.x[30] == lr); /* XZR destination */
    before = s;
    CHECK(n10_step_pac(0xd503201fU, &s, &c) == N10_PACSTEP_UNSUPPORTED && memcmp(&s, &before, sizeof(s)) == 0);
    CHECK(n10_step_pac(0xdac10020U, &s, NULL) == N10_PACSTEP_BAD_CONTEXT);
    CHECK(n10_step_pac(0xdac10020U, NULL, &c) == N10_PACSTEP_BAD_CONTEXT);
    CHECK(!n10_decode_pac(0xdac10020U, NULL));
    s.pc = UINT64_MAX - 3;
    CHECK(n10_step_pac(0xdac10020U, &s, &c) == N10_PACSTEP_BAD_CONTEXT);
    printf("{\"oracle_records\":%u,\"assertions\":%u,\"passed\":true}\n", records, checks);
    return 0;
}
