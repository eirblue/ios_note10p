/* New scalar C promotions/count boundaries; no allocation or kernel API calls. */
#include <stdio.h>
#include "memdev-arithmetic.h"

#define CHECK(expr) do { ++checks; if (!(expr)) { \
    fprintf(stderr, "case %u check %u failed\n", case_id, checks); return 1; \
} } while (0)

int main(void)
{
    unsigned case_id = 1, checks = 0;
    uint32_t pages = UINT32_C(0x100000);
    uint64_t extent = UINT64_C(0x100000000);
    CHECK(n10_extent(pages) == extent);
    CHECK(n10_blocks(pages, 512) == UINT64_C(8388608));
    CHECK(n10_eof(pages, extent));
    CHECK(n10_char_count(pages, 8192, (int64_t)extent) == 0);

    case_id = 2;
    pages = UINT32_C(0x100001);
    CHECK(n10_extent(pages) == UINT64_C(0x100001000));
    CHECK(n10_char_count(pages, 8192, INT64_C(0x100000000)) == 4096);
    CHECK(n10_strategy_count(pages, UINT64_C(0x100000000), 8192) == 4096);

    case_id = 3;
    extent = UINT64_C(9571401728);
    pages = (uint32_t)(extent >> 12);
    CHECK(n10_extent(pages) == extent);
    CHECK(n10_blocks(pages, 512) == extent / 512);
    CHECK(n10_blocks(pages, 4096) == extent / 4096);

    case_id = 4;
    extent = UINT64_C(5247074304);
    pages = (uint32_t)(extent >> 12);
    CHECK(n10_extent(pages) == extent);
    CHECK(n10_blocks(pages, 512) == extent / 512);
    CHECK(n10_blocks(pages, 4096) == extent / 4096);

    case_id = 5;
    pages = UINT32_MAX;
    extent = UINT64_C(0xffffffff000);
    CHECK(n10_extent(pages) == extent);
    CHECK(n10_blocks(pages, INT_MAX) == 8193);

    case_id = 6;
    CHECK(n10_char_count(pages, (int64_t)INT_MAX + 1, 0) == INT_MAX);
    CHECK(n10_char_count(pages, 4096, 0) == 4096);
    CHECK(n10_char_count(pages, 0, 0) == 0);

    case_id = 7;
    CHECK(n10_char_count(pages, 8192, (int64_t)extent - 512) == 512);
    CHECK(!n10_eof(pages, extent - 512));
    CHECK(n10_eof(pages, extent));
    CHECK(n10_eof(pages, extent + 512));
    CHECK(n10_char_count(pages, 8192, (int64_t)extent + 512) == 0);

    case_id = 8;
    pages = UINT32_C(0x100000);
    extent = UINT64_C(0x100000000);
    unsigned int left = UINT32_MAX;
    CHECK(left == UINT32_MAX);
    CHECK(n10_strategy_count(pages, 0, UINT32_MAX) == UINT32_MAX);
    CHECK(n10_strategy_count(pages, extent - 4096, UINT32_MAX) == 4096);

    case_id = 9;
    pages = UINT32_MAX;
    extent = UINT64_C(0xffffffff000);
    uint64_t blkoff = extent - 512;
    CHECK(blkoff / 512 <= (uint64_t)INT64_MAX / 512);
    CHECK(blkoff + UINT32_MAX > blkoff);
    CHECK(blkoff + UINT32_MAX < UINT64_MAX);
    CHECK(!n10_eof(pages, blkoff));
    CHECK(n10_strategy_count(pages, blkoff, UINT32_MAX) == 512);
    printf("{\"passed\":true,\"cases\":9,\"checks\":%u}\n", checks);
    return 0;
}
