/* SPDX-License-Identifier: GPL-2.0-only */
/* NEW shared-helper output fixture. No carrier, crypto or decoder linkage. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#define N10_COMPARE_CLEAR(p,n) memset((p),0,(n))
#include "linux_data_compare_evidence.h"
#undef N10_COMPARE_CLEAR

static unsigned int zeroed(const void *value, size_t size)
{
    const unsigned char *bytes = value;
    size_t i;
    for (i = 0; i < size; ++i) if (bytes[i]) return 0;
    return 1;
}

static uint32_t checksum(const char *body, int count)
{
    uint32_t value = 2166136261U;
    int i;
    for (i = 0; i < count; ++i) value = (value ^ (unsigned char)body[i]) * 16777619U;
    return value;
}

static int one_case(const char *name, unsigned int evaluated, unsigned int equal,
    unsigned long long logical, unsigned int first)
{
    struct n10_data_compare_evidence evidence = {{0},{0},0,0};
    unsigned char actual[32], expected[32];
    char body[384], actual_hex[65], expected_hex[65];
    unsigned int i, copied = 1, scratch, cleared;
    int count;
    memset(actual, 0x11, sizeof(actual));
    memset(expected, equal ? 0x11 : 0x22, sizeof(expected));
    if (evaluated)
        n10_data_compare_capture(&evidence, actual, expected, equal ? 0 : 1);
    memset(actual, 0xa5, sizeof(actual)); memset(expected, 0xa5, sizeof(expected));
    for (i = 0; i < 32; ++i) {
        if (evidence.actual[i] != (evaluated ? 0x11 : 0) ||
            evidence.expected[i] != (evaluated ? (equal ? 0x11 : 0x22) : 0)) copied = 0;
    }
    count = n10_data_compare_format(&evidence, body, sizeof(body), actual_hex, expected_hex,
        "11111111111111111111111111111111", "22222222222222222222222222222222", logical);
    scratch = zeroed(actual_hex, sizeof(actual_hex)) && zeroed(expected_hex, sizeof(expected_hex));
    n10_data_compare_clear(&evidence);
    cleared = zeroed(&evidence, sizeof(evidence));
    if (!count || !copied || !scratch || !cleared) return 0;
    printf("%s{\"name\":\"%s\",\"length\":%d,\"copied\":%u,\"scratch_cleared\":%u,\"cleared\":%u,\"frame\":\"N10BOOTLINK2 boot=33333333333333333333333333333333 N10DATACMP1 %s checksum=%08x\"}",
        first ? "" : ",", name, count, copied, scratch, cleared, body, checksum(body,count));
    memset(body, 0, sizeof(body));
    return 1;
}

int main(void)
{
    struct n10_data_compare_evidence evidence = {{0},{0},0,0};
    struct { unsigned char before[8]; char body[8]; unsigned char after[8]; } guarded;
    char actual[65], expected[65];
    unsigned int i, short_ok;
    int count;
    printf("{\"cases\":[");
    if (!one_case("unequal",1,0,4000,1) || !one_case("equal",1,1,4000,0) ||
        !one_case("unavailable",0,0,0,0) || !one_case("maximum",0,0,67108864,0)) return 1;
    memset(&guarded, 0xa5, sizeof(guarded));
    count = n10_data_compare_format(&evidence,guarded.body,sizeof(guarded.body),actual,expected,
        "11111111111111111111111111111111","22222222222222222222222222222222",67108864);
    short_ok = count == 0 && zeroed(guarded.body,sizeof(guarded.body)) &&
        zeroed(actual,sizeof(actual)) && zeroed(expected,sizeof(expected));
    for (i=0;i<8;++i) if (guarded.before[i] != 0xa5 || guarded.after[i] != 0xa5) short_ok = 0;
    n10_data_compare_clear(&evidence);
    printf("],\"short_buffer_rejected\":%u,\"hash_calls\":0,\"decoder_calls\":0}\n",short_ok);
    return short_ok ? 0 : 1;
}
