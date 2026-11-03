/* SPDX-License-Identifier: GPL-2.0-only */
/* NEW shared late-prefix helper fixture; no native hash/decoder linkage. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

static unsigned int cleared_eight, clear_failed;
static void fixture_clear(void *p, size_t size)
{
    size_t i;
    memset(p,0,size);
    if (size == 8) {
        ++cleared_eight;
        for (i=0;i<size;++i) if (((unsigned char *)p)[i]) clear_failed = 1;
    }
}
#define N10_COMPARE_CLEAR(p,n) fixture_clear((p),(n))
#include "linux_data_compare_evidence.h"
#undef N10_COMPARE_CLEAR

static unsigned int zeroed(const void *p, size_t size)
{
    const unsigned char *bytes = p;
    size_t i;
    for (i=0;i<size;++i) if (bytes[i]) return 0;
    return 1;
}

static uint32_t checksum(const char *body, int count)
{
    uint32_t value = 2166136261U;
    int i;
    for (i=0;i<count;++i) value = (value ^ (unsigned char)body[i]) * 16777619U;
    return value;
}

static int one_case(const char *name, const unsigned char *input,
    unsigned long long logical, unsigned int first)
{
    struct n10_data_compare_evidence evidence = {0};
    unsigned char actual[32], expected[32];
    char body[448], actual_hex[65], expected_hex[65];
    unsigned int sampled, magic, zeros, cleared, scratch;
    int count;
    memset(actual,0x11,sizeof(actual)); memset(expected,0x22,sizeof(expected));
    if (input) n10_data_compare_capture(&evidence,actual,expected,1);
    /* Unavailable uses NULL to demonstrate that the helper performs no read. */
    n10_data_input_probe(&evidence,input);
    sampled=evidence.sampled; magic=evidence.magic_match; zeros=evidence.prefix_zero;
    count=n10_data_compare_format(&evidence,body,sizeof(body),actual_hex,expected_hex,
        "11111111111111111111111111111111","22222222222222222222222222222222",logical);
    scratch=zeroed(actual_hex,sizeof(actual_hex)) && zeroed(expected_hex,sizeof(expected_hex));
    n10_data_compare_clear(&evidence); cleared=zeroed(&evidence,sizeof(evidence));
    if (!count || !scratch || !cleared) return 0;
    printf("%s{\"name\":\"%s\",\"length\":%d,\"sampled\":%u,\"magic_match\":%u,\"prefix_zero\":%u,\"cleared\":%u,\"scratch_cleared\":%u,\"frame\":\"N10BOOTLINK2 boot=33333333333333333333333333333333 N10DATACMP2 %s checksum=%08x\"}",
        first ? "" : ",",name,count,sampled,magic,zeros,cleared,scratch,body,checksum(body,count));
    fixture_clear(body,sizeof(body));
    return 1;
}

int main(void)
{
    const unsigned char magic[8]={'N','1','0','D','A','T','A','1'};
    const unsigned char zero[8]={0}, other[8]={'O','T','H','E','R','1','2','3'};
    struct n10_data_compare_evidence unavailable={0};
    struct { unsigned char before[8]; char body[8]; unsigned char after[8]; } guarded;
    char actual[65],expected[65];
    unsigned int i, sampled_clears, short_ok;
    int count;
    printf("{\"evidence_bytes\":%zu,\"body_cap\":%u,\"frame_capacity\":448,\"cases\":[",
        sizeof(unavailable),N10_DATA_COMPARE_BODY_MAX);
    if (!one_case("magic",magic,4000,1) || !one_case("zero",zero,4000,0) ||
        !one_case("other",other,4000,0) || !one_case("unavailable",NULL,0,0) ||
        !one_case("maximum",NULL,67108864,0)) return 1;
    sampled_clears=cleared_eight;
    memset(&guarded,0xa5,sizeof(guarded));
    count=n10_data_compare_format(&unavailable,guarded.body,sizeof(guarded.body),actual,expected,
        "11111111111111111111111111111111","22222222222222222222222222222222",67108864);
    short_ok=count==0 && zeroed(guarded.body,sizeof(guarded.body)) &&
        zeroed(actual,sizeof(actual)) && zeroed(expected,sizeof(expected));
    for(i=0;i<8;++i) if(guarded.before[i]!=0xa5 || guarded.after[i]!=0xa5) short_ok=0;
    n10_data_compare_clear(&unavailable);
    printf("],\"sampled_scratch_clears\":%u,\"clear_failed\":%u,\"short_buffer_rejected\":%u,\"hash_calls\":0,\"decoder_calls\":0}\n",
        sampled_clears,clear_failed,short_ok);
    return short_ok && sampled_clears==3 && !clear_failed ? 0 : 1;
}
