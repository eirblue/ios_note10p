#include "hint_sites.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks, real_sites;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); return 1; } } while (0)
static uint64_t le(const unsigned char *p, unsigned n)
{ uint64_t v = 0; for (unsigned i = 0; i < n; ++i) v |= (uint64_t)p[i] << (8*i); return v; }
int main(int argc, char **argv)
{
    CHECK(argc > 1);
    struct n10_fixup_pac_context context = {
        {{48,0,5},{48,0,5}}, {{1,2},{3,4},{5,6},{7,8}}, 15, NULL, NULL
    };
    CHECK(!n10_hint_table_validate(NULL));
    struct n10_hint_site bad[] = {{4,0xd503233fU},{4,0xd503233fU}};
    struct n10_hint_table invalid = {bad,2,0};
    CHECK(!n10_hint_table_validate(&invalid));
    invalid.count = 1; bad[0].original_word = 0xdac10000U;
    CHECK(!n10_hint_table_validate(&invalid)); /* PAC register form is not a hint. */
    bad[0].original_word = 0xd503233fU; invalid.slide = UINT64_MAX - 3;
    CHECK(!n10_hint_table_validate(&invalid));
    invalid.slide = 2; CHECK(!n10_hint_table_validate(&invalid));
    for (int file = 1; file < argc; ++file) {
        FILE *f = fopen(argv[file],"rb"); CHECK(f);
        unsigned char record[12]; CHECK(fread(record,1,4,f) == 4);
        size_t count = (size_t)le(record,4); CHECK(count <= 100000);
        struct n10_hint_site *sites = calloc(count ? count : 1,sizeof(*sites)); CHECK(sites);
        for (size_t i = 0; i < count; ++i) {
            CHECK(fread(record,1,12,f) == 12);
            sites[i].address = le(record,8); sites[i].original_word = (uint32_t)le(record+8,4);
        }
        CHECK(fgetc(f) == EOF && !ferror(f)); CHECK(fclose(f) == 0);
        real_sites += (unsigned)count;
        const uint64_t slides[] = {0,0x4000,0x100000000ULL};
        for (unsigned slide = 0; slide < 3; ++slide) {
            struct n10_hint_table table = {sites,count,slides[slide]};
            CHECK(n10_hint_table_validate(&table));
            for (size_t i = 0; i < count; ++i) {
                struct n10_pac_instruction d;
                CHECK(n10_decode_pac(sites[i].original_word,&d) && d.hint_encoding);
                struct n10_user_state state = {{0},0x8000,sites[i].address+table.slide};
                state.x[16] = 0x1234; state.x[17] = state.x[30] = 0x4000;
                if (d.operation == N10_PAC_AUTH) {
                    uint64_t modifier = d.modifier_kind == N10_MOD_SP ? state.sp :
                        d.modifier_kind == N10_MOD_ZERO ? 0 : state.x[d.modifier_register];
                    CHECK(n10_pac_sign(&context.profiles[0],&context.keys[d.key],0x4000,
                                      modifier,&state.x[d.destination]) == N10_PAC_OK);
                }
                struct n10_user_state before = state;
                CHECK(n10_hint_dispatch(&table,N10_HINT_BRK ^ 32,&state,&context) == N10_HINT_WORD_MISMATCH);
                CHECK(memcmp(&before,&state,sizeof(state)) == 0);
                struct n10_fixup_pac_context missing = context; missing.present_mask = 0;
                if (d.operation != N10_PAC_STRIP) {
                    CHECK(n10_hint_dispatch(&table,N10_HINT_BRK,&state,&missing) == N10_HINT_MODEL_FAILED);
                    CHECK(memcmp(&before,&state,sizeof(state)) == 0);
                }
                CHECK(n10_hint_dispatch(&table,N10_HINT_BRK,&state,&context) == N10_HINT_OK);
                CHECK(state.pc == before.pc + 4 && state.sp == before.sp);
                for (unsigned r = 0; r < 31; ++r) if (r != d.destination) CHECK(state.x[r] == before.x[r]);
                if (d.operation != N10_PAC_SIGN) CHECK(state.x[d.destination] == 0x4000);
            }
            struct n10_user_state unknown = {{0},0,UINT64_C(0x700000000000)+table.slide}, before = unknown;
            CHECK(n10_hint_dispatch(&table,N10_HINT_BRK,&unknown,&context) == N10_HINT_NOT_REGISTERED);
            CHECK(memcmp(&before,&unknown,sizeof(before)) == 0);
        }
        free(sites);
    }
    printf("{\"real_hint_sites\":%u,\"assertions\":%u,\"passed\":true}\n",real_sites,checks);
    return 0;
}
