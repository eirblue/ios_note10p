#ifndef NOTE10_FIXUP24_H
#define NOTE10_FIXUP24_H
#include <stddef.h>
#include <stdint.h>

/* DYLD_CHAINED_PTR_ARM64E_USERLAND24 (12) only. No relocation/signing occurs. */
struct n10_fixup24 {
    uint64_t target;
    int32_t addend;
    uint32_t ordinal;
    uint16_t diversity, next_bytes;
    uint8_t bind, authenticated, key, address_diversity, high8;
};
int n10_decode_fixup24(uint64_t raw, struct n10_fixup24 *out);
typedef int (*n10_visit_fixup24)(void *context, size_t offset, uint64_t raw,
                               const struct n10_fixup24 *decoded);
enum n10_walk24_result {
    N10_WALK24_OK, N10_WALK24_BAD_INPUT, N10_WALK24_BOUNDS,
    N10_WALK24_ENCODING, N10_WALK24_VISITOR_STOPPED
};
/* Caller supplies one readable page and a non-mutating visitor. Bounds are
 * checked before every eight-byte read. A stopped walk is not transactional:
 * earlier visitor callbacks have already occurred. This API never writes page.
 */
enum n10_walk24_result n10_walk_fixup24_page(const uint8_t *page, size_t size,
                                           uint16_t start, n10_visit_fixup24 visit,
                                           void *context);
#endif
