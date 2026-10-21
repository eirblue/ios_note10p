#include "fixup_value.h"
#include "import_table.h"
#include "fixup-chains.h" /* Pinned test-only Apple reference. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); return 1; } } while (0)
union ref_ptr {
    uint64_t raw;
    struct dyld_chained_ptr_arm64e_rebase r;
    struct dyld_chained_ptr_arm64e_bind24 b;
    struct dyld_chained_ptr_arm64e_auth_rebase ar;
};
struct signer { unsigned calls; uint8_t key, addr; uint16_t diversity; uint64_t slot, pointer; int ok; };
/* Test-only callback; deliberately not a PAC implementation. */
static int fake_sign(void *opaque, uint8_t key, uint16_t div, uint8_t addr,
                     uint64_t slot, uint64_t pointer, uint64_t *out)
{
    struct signer *s = opaque;
    ++s->calls; s->key = key; s->diversity = div; s->addr = addr; s->slot = slot; s->pointer = pointer;
    *out = pointer ^ 0x1200000000000000ULL;
    return s->ok;
}
static uint32_t read32(const uint8_t *p) { uint32_t v; memcpy(&v, p, 4); return v; }
static void put32(uint8_t *p, uint32_t v) { memcpy(p, &v, 4); }
static int imports_file(const char *path, unsigned *parsed)
{
    FILE *f = fopen(path, "rb"); CHECK(f != NULL);
    CHECK(fseek(f, 0, SEEK_END) == 0); long n = ftell(f);
    CHECK(n >= 28 && n < 1024 * 1024); CHECK(fseek(f, 0, SEEK_SET) == 0);
    uint8_t *b = malloc((size_t)n); CHECK(b != NULL);
    CHECK(fread(b, 1, (size_t)n, f) == (size_t)n); CHECK(fclose(f) == 0);
    uint32_t offset = read32(b + 8), symbols = read32(b + 12), count = read32(b + 16);
    CHECK(read32(b + 20) == 1 && read32(b + 24) == 0);
    for (uint32_t i = 0; i < count; ++i) {
        struct dyld_chained_import ref;
        memcpy(&ref, b + offset + 4 * i, sizeof(ref));
        struct n10_import d;
        CHECK(n10_import_at(b, (size_t)n, i, &d) == N10_IMPORT_OK);
        int32_t ordinal = ref.lib_ordinal;
        if (ordinal > 240) ordinal -= 256;
        CHECK(d.library_ordinal == ordinal && d.weak == ref.weak_import && d.addend == 0);
        CHECK(strcmp(d.name, (const char *)(b + symbols + ref.name_offset)) == 0);
        CHECK(d.name_length == strlen(d.name)); ++*parsed;
    }
    struct n10_import d;
    CHECK(n10_import_at(b, (size_t)n, count, &d) == N10_IMPORT_BOUNDS);
    free(b); return 0;
}
int main(int argc, char **argv)
{
    CHECK(argc == 5);
    uint64_t targets[1024];
    for (unsigned i = 0; i < 1024; ++i) targets[i] = i % 17 == 0 ? 0 : 0x200000000ULL + 0x1000 * i;
    FILE *f = fopen(argv[1], "rb"); CHECK(f != NULL);
    union ref_ptr a; unsigned records = 0; size_t bytes;
    while ((bytes = fread(&a.raw, 1, 8, f)) != 0) {
        CHECK(bytes == 8);
        uint64_t out = 0xfeed, expected = 0;
        struct signer s = {0}; s.ok = 1;
        enum n10_value_result want;
        if (a.r.bind && a.b.zero != 0) want = N10_VALUE_ENCODING;
        else if (a.r.bind && a.b.ordinal >= 1024) want = N10_VALUE_BAD_ORDINAL;
        else {
            want = N10_VALUE_OK;
            if (a.r.bind) {
                expected = targets[a.b.ordinal];
                if (!a.r.auth) {
                    int32_t addend = (int32_t)(a.b.addend << 13) >> 13;
                    if (addend < 0 && expected < (uint64_t)(-(int64_t)addend)) want = N10_VALUE_OVERFLOW;
                    else expected += (uint64_t)(int64_t)addend;
                }
            } else expected = 0x100000000ULL + (a.r.auth ? a.ar.target : (a.r.target | ((uint64_t)a.r.high8 << 56)));
            if (want == N10_VALUE_OK && a.r.auth && !(a.r.bind && expected == 0)) expected ^= 0x1200000000000000ULL;
        }
        CHECK(n10_fixup24_value(a.raw, 0x100000000ULL, 0x100004008ULL, targets, 1024, fake_sign, &s, &out) == want);
        CHECK(out == (want == N10_VALUE_OK ? expected : 0xfeed));
        if (want == N10_VALUE_OK && a.r.auth && s.calls) {
            CHECK(s.key == a.ar.key && s.diversity == a.ar.diversity && s.addr == a.ar.addrDiv);
            CHECK(s.slot == 0x100004008ULL && (s.pointer ^ 0x1200000000000000ULL) == out);
        }
        ++records;
    }
    CHECK(!ferror(f)); CHECK(fclose(f) == 0);
    uint64_t out = 0x1234, one = 0x4000;
    CHECK(n10_fixup24_value(1ULL << 63, 0x1000, 0x2000, NULL, 0, NULL, NULL, &out) == N10_VALUE_NEEDS_SIGN && out == 0x1234);
    struct signer s = {0}; s.ok = 0;
    CHECK(n10_fixup24_value(1ULL << 63, 0x1000, 0x2000, NULL, 0, fake_sign, &s, &out) == N10_VALUE_SIGN_FAILED && out == 0x1234);
    CHECK(n10_fixup24_value(1, UINT64_MAX, 0, NULL, 0, NULL, NULL, &out) == N10_VALUE_OVERFLOW && out == 0x1234);
    CHECK(n10_fixup24_value(1ULL << 62, 0, 0, NULL, 1, NULL, NULL, &out) == N10_VALUE_BAD_INPUT && out == 0x1234);
    CHECK(n10_fixup24_value(0, 0, 0, NULL, 0, NULL, NULL, NULL) == N10_VALUE_BAD_INPUT);
    one = UINT64_MAX;
    CHECK(n10_fixup24_value((1ULL << 62) | (1ULL << 32), 0, 0, &one, 1, NULL, NULL, &out) == N10_VALUE_OVERFLOW);
    one = 0;
    CHECK(n10_fixup24_value(3ULL << 62, 0, 0, &one, 1, NULL, NULL, &out) == N10_VALUE_OK && out == 0);
    unsigned parsed = 0;
    for (int i = 2; i < argc; ++i) CHECK(imports_file(argv[i], &parsed) == 0);
    /* Synthetic formats 2/3 encoded with Apple's native bitfields. */
    uint8_t blob[64] = {0}; put32(blob + 8, 28); put32(blob + 12, 48); put32(blob + 16, 1); put32(blob + 20, 2);
    memcpy(blob + 48, "_demo", 6);
    struct dyld_chained_import_addend r2 = {0}; r2.lib_ordinal = 255; r2.weak_import = 1; r2.addend = INT32_MIN;
    memcpy(blob + 28, &r2, sizeof(r2)); struct n10_import d;
    CHECK(n10_import_at(blob, sizeof(blob), 0, &d) == N10_IMPORT_OK);
    CHECK(d.library_ordinal == -1 && d.weak == 1 && d.addend == INT32_MIN && d.name_length == 5);
    put32(blob + 20, 3);
    struct dyld_chained_import_addend64 r3 = {0}; r3.lib_ordinal = 65521; r3.addend = 1ULL << 63;
    memcpy(blob + 28, &r3, sizeof(r3));
    CHECK(n10_import_at(blob, sizeof(blob), 0, &d) == N10_IMPORT_OK && d.library_ordinal == -15 && d.addend == INT64_MIN);
    r3.lib_ordinal = 65520; r3.addend = INT64_MAX; memcpy(blob + 28, &r3, sizeof(r3));
    CHECK(n10_import_at(blob, sizeof(blob), 0, &d) == N10_IMPORT_OK && d.library_ordinal == 65520 && d.addend == INT64_MAX);
    struct n10_import saved; memcpy(&saved, &d, sizeof(d));
    r3.reserved = 1; memcpy(blob + 28, &r3, sizeof(r3));
    CHECK(n10_import_at(blob, sizeof(blob), 0, &d) == N10_IMPORT_ENCODING && memcmp(&d, &saved, sizeof(d)) == 0);
    r3.reserved = 0; r3.name_offset = UINT32_MAX; memcpy(blob + 28, &r3, sizeof(r3));
    CHECK(n10_import_at(blob, sizeof(blob), 0, &d) == N10_IMPORT_BOUNDS);
    r3.name_offset = 0; memcpy(blob + 28, &r3, sizeof(r3)); memset(blob + 48, 'a', 16);
    CHECK(n10_import_at(blob, sizeof(blob), 0, &d) == N10_IMPORT_BOUNDS);
    blob[48] = 0; CHECK(n10_import_at(blob, sizeof(blob), 0, &d) == N10_IMPORT_ENCODING);
    put32(blob + 24, 1); CHECK(n10_import_at(blob, sizeof(blob), 0, &d) == N10_IMPORT_UNSUPPORTED);
    CHECK(n10_import_at(NULL, 64, 0, &d) == N10_IMPORT_BAD_INPUT);
    CHECK(n10_import_at(blob, 27, 0, &d) == N10_IMPORT_BOUNDS);
    printf("{\"records\":%u,\"real_imports\":%u,\"assertions\":%u,\"passed\":true}\n", records, parsed, checks);
    return 0;
}
