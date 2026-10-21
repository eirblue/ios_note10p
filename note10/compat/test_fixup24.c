#include "fixup24.h"
/* Test-only reference. Fetched with original Apple license, not embedded in
 * the implementation or copied into this repository's tracked source. */
#include "fixup-chains.h"
#include <stdio.h>
#include <string.h>

#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error This bitfield reference test requires little endian
#endif
static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); return 1; } } while (0)
union apple_ref {
    uint64_t raw;
    struct dyld_chained_ptr_arm64e_rebase r;
    struct dyld_chained_ptr_arm64e_bind24 b;
    struct dyld_chained_ptr_arm64e_auth_rebase ar;
    struct dyld_chained_ptr_arm64e_auth_bind24 ab;
};
struct visit_state { unsigned count, stop; size_t last; };
static int visit(void *ctx, size_t offset, uint64_t raw, const struct n10_fixup24 *d)
{
    (void)raw; (void)d;
    struct visit_state *v = ctx;
    ++v->count; v->last = offset;
    return v->count != v->stop;
}
static void store(uint8_t *p, uint64_t word)
{
    for (unsigned i = 0; i < 8; ++i) p[i] = (uint8_t)(word >> (8 * i));
}
int main(int argc, char **argv)
{
    CHECK(argc == 3);
    CHECK(sizeof(union apple_ref) == 8);
    FILE *f = fopen(argv[1], "rb"); CHECK(f != NULL);
    unsigned records = 0;
    union apple_ref a;
    size_t bytes;
    while ((bytes = fread(&a.raw, 1, 8, f)) != 0) {
        CHECK(bytes == 8);
        struct n10_fixup24 d, before;
        memset(&before, 0xa5, sizeof(before)); memcpy(&d, &before, sizeof(d));
        int expected = !a.r.bind || (a.r.auth ? a.ab.zero == 0 : a.b.zero == 0);
        int got = n10_decode_fixup24(a.raw, &d);
        CHECK(got == expected);
        if (!got) {
            CHECK(memcmp(&d, &before, sizeof(d)) == 0);
        } else {
            CHECK(d.authenticated == a.r.auth); CHECK(d.bind == a.r.bind);
            CHECK(d.next_bytes == a.r.next * 8);
            CHECK(d.ordinal == (a.r.bind ? a.b.ordinal : 0));
            if (a.r.auth) {
                CHECK(d.target == (a.r.bind ? 0 : a.ar.target));
                CHECK(d.diversity == a.ar.diversity); CHECK(d.address_diversity == a.ar.addrDiv);
                CHECK(d.key == a.ar.key); CHECK(d.high8 == 0 && d.addend == 0);
            } else if (a.r.bind) {
                /* Signed extraction through the Apple compiler bitfield. */
                int32_t addend = (int32_t)(a.b.addend << 13) >> 13;
                CHECK(d.addend == addend);
                CHECK(d.target == 0 && d.key == 0 && d.high8 == 0 && d.diversity == 0 && d.address_diversity == 0);
            } else {
                CHECK(d.target == a.r.target); CHECK(d.high8 == a.r.high8);
                CHECK(d.addend == 0 && d.key == 0 && d.diversity == 0 && d.address_diversity == 0);
            }
        }
        ++records;
    }
    CHECK(!ferror(f)); CHECK(fclose(f) == 0); CHECK(records > 20000);
    f = fopen(argv[2], "rb"); CHECK(f != NULL);
    uint32_t pages; CHECK(fread(&pages, sizeof(pages), 1, f) == 1);
    uint8_t page[16384], backup[16384];
    unsigned real_visits = 0;
    for (uint32_t i = 0; i < pages; ++i) {
        uint32_t size, count; uint16_t start, reserved;
        CHECK(fread(&size, 4, 1, f) == 1); CHECK(fread(&start, 2, 1, f) == 1);
        CHECK(fread(&reserved, 2, 1, f) == 1); CHECK(fread(&count, 4, 1, f) == 1);
        CHECK(reserved == 0 && (size == 4096 || size == 16384));
        CHECK(fread(page, 1, size, f) == size); memcpy(backup, page, size);
        struct visit_state v = {0, 0, 0};
        CHECK(n10_walk_fixup24_page(page, size, start, visit, &v) == N10_WALK24_OK);
        CHECK(v.count == count); CHECK(memcmp(page, backup, size) == 0);
        real_visits += v.count;
    }
    CHECK(fgetc(f) == EOF && !ferror(f)); CHECK(fclose(f) == 0);
    memset(page, 0, sizeof(page));
    struct visit_state v = {0, 0, 0};
    CHECK(n10_walk_fixup24_page(page, 4096, 0xffff, visit, &v) == N10_WALK24_OK && v.count == 0);
    CHECK(n10_walk_fixup24_page(page, 4096, 4090, visit, &v) == N10_WALK24_BOUNDS);
    CHECK(n10_walk_fixup24_page(page, 4096, 0x8000, visit, &v) == N10_WALK24_BAD_INPUT);
    CHECK(n10_walk_fixup24_page(NULL, 4096, 0, visit, &v) == N10_WALK24_BAD_INPUT);
    CHECK(n10_walk_fixup24_page(page, 4096, 0, NULL, &v) == N10_WALK24_BAD_INPUT);
    CHECK(n10_walk_fixup24_page(page, 3000, 0, visit, &v) == N10_WALK24_BAD_INPUT);
    store(page, (1ULL << 62) | (1ULL << 24));
    CHECK(n10_walk_fixup24_page(page, 4096, 0, visit, &v) == N10_WALK24_ENCODING && v.count == 0);
    store(page, 512ULL << 51);
    CHECK(n10_walk_fixup24_page(page, 4096, 0, visit, &v) == N10_WALK24_BOUNDS && v.count == 1);
    v.count = 0; v.stop = 1; store(page, 1ULL << 51); store(page + 8, 0);
    CHECK(n10_walk_fixup24_page(page, 4096, 0, visit, &v) == N10_WALK24_VISITOR_STOPPED && v.count == 1);
    v.count = 0; v.stop = 0;
    CHECK(n10_walk_fixup24_page(page, 4096, 0, visit, &v) == N10_WALK24_OK && v.count == 2 && v.last == 8);
    CHECK(n10_decode_fixup24(0, NULL) == 0);
    printf("{\"records\":%u,\"real_pages\":%u,\"real_fixups\":%u,\"assertions\":%u,\"passed\":true}\n", records, pages, real_visits, checks);
    return 0;
}
