/* Lzma decompressor for Linux kernel. Shamelessly snarfed
 *from busybox 1.1.1
 *
 *Linux kernel adaptation
 *Copyright (C) 2006  Alain < alain@knaff.lu >
 *
 *Based on small lzma deflate implementation/Small range coder
 *implementation for lzma.
 *Copyright (C) 2006  Aurelien Jacobs < aurel@gnuage.org >
 *
 *Based on LzmaDecode.c from the LZMA SDK 4.22 (http://www.7-zip.org/)
 *Copyright (C) 1999-2005  Igor Pavlov
 *
 *Copyrights of the parts, see headers below.
 *
 *
 *This program is free software; you can redistribute it and/or
 *modify it under the terms of the GNU Lesser General Public
 *License as published by the Free Software Foundation; either
 *version 2.1 of the License, or (at your option) any later version.
 *
 *This program is distributed in the hope that it will be useful,
 *but WITHOUT ANY WARRANTY; without even the implied warranty of
 *MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *Lesser General Public License for more details.
 *
 *You should have received a copy of the GNU Lesser General Public
 *License along with this library; if not, write to the Free Software
 *Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 */
/* Permanent bounded port of pinned Linux lib/decompress_unlzma.c.
 * Range/literal/match coding follows the original implementation above.
 * No PREBOOT, init sections, allocator, refill/error callbacks or globals.
 * Only lc3/lp0/pb2, 8MiB dictionary and finite-size ALONE are admitted.
 */
#include "carrier_lzma.h"

/* Small range coder, Copyright (C) 2006 Aurelien Jacobs.
 * Based on LzmaDecode.c, Copyright (C) 1999-2005 Igor Pavlov. */
struct rc {
    const uint8_t *input;
    size_t size, pos;
    uint32_t code, range;
    uint16_t *p;
};

static int normalize(struct rc *rc)
{
    if (rc->range < (1u << 24)) {
        if (rc->pos == rc->size) return N10_LZMA_INPUT;
        rc->range <<= 8;
        rc->code = (rc->code << 8) | rc->input[rc->pos++];
    }
    return 0;
}

static int bit(struct rc *rc, size_t index)
{
    uint16_t *p;
    uint32_t bound;
    int status = normalize(rc);
    if (status) return status;
    if (index >= N10_LZMA_WORKSPACE / sizeof(uint16_t)) return N10_LZMA_CORRUPT;
    p = rc->p + index;
    bound = (uint32_t)*p * (rc->range >> 11);
    if (rc->code < bound) {
        rc->range = bound;
        *p = (uint16_t)(*p + ((2048u - *p) >> 5));
        return 0;
    }
    rc->range -= bound;
    rc->code -= bound;
    *p = (uint16_t)(*p - (*p >> 5));
    return 1;
}

static int direct_bit(struct rc *rc)
{
    int status = normalize(rc);
    if (status) return status;
    rc->range >>= 1;
    if (rc->code >= rc->range) {
        rc->code -= rc->range;
        return 1;
    }
    return 0;
}

static int tree(struct rc *rc, size_t base, unsigned levels, uint32_t *value)
{
    uint32_t symbol = 1;
    unsigned i;
    for (i = 0; i < levels; ++i) {
        int b = bit(rc, base + symbol);
        if (b < 0) return b;
        symbol = symbol * 2u + (unsigned)b;
    }
    *value = symbol - (1u << levels);
    return 0;
}

/* Small lzma implementation, Copyright (C) 2006 Aurelien Jacobs.
 * Based on LzmaDecode.c, Copyright (C) 1999-2005 Igor Pavlov. */
#define LZMA_LEN_CHOICE 0u
#define LZMA_LEN_CHOICE_2 1u
#define LZMA_LEN_LOW 2u
#define LZMA_LEN_MID 130u
#define LZMA_LEN_HIGH 258u
#define LZMA_NUM_LEN_PROBS 514u
#define LZMA_IS_MATCH 0u
#define LZMA_IS_REP 192u
#define LZMA_IS_REP_G0 204u
#define LZMA_IS_REP_G1 216u
#define LZMA_IS_REP_G2 228u
#define LZMA_IS_REP_0_LONG 240u
#define LZMA_POS_SLOT 432u
#define LZMA_SPEC_POS 688u
#define LZMA_ALIGN 802u
#define LZMA_LEN_CODER 818u
#define LZMA_REP_LEN_CODER (LZMA_LEN_CODER + LZMA_NUM_LEN_PROBS)
#define LZMA_LITERAL (LZMA_REP_LEN_CODER + LZMA_NUM_LEN_PROBS)

struct writer {
    uint8_t *data;
    size_t pos, size;
    uint32_t state, rep[4];
    uint8_t previous;
};

static int copy_match(struct writer *w, uint32_t distance, uint32_t count)
{
    if (!distance || distance > (1u << 23) || distance > w->pos) return N10_LZMA_CORRUPT;
    if (count > w->size - w->pos) return N10_LZMA_OUTPUT;
    while (count--) {
        w->previous = w->data[w->pos - distance];
        w->data[w->pos++] = w->previous;
    }
    return 0;
}

static int literal(struct rc *rc, struct writer *w)
{
    size_t base = LZMA_LITERAL + 768u * (w->previous >> 5);
    uint32_t symbol = 1;
    if (w->state >= 7) {
        unsigned match;
        if (!w->rep[0] || w->rep[0] > w->pos || w->rep[0] > (1u << 23)) return N10_LZMA_CORRUPT;
        match = w->data[w->pos - w->rep[0]];
        do {
            unsigned match_bit;
            int b;
            match <<= 1;
            match_bit = match & 0x100u;
            b = bit(rc, base + 0x100u + match_bit + symbol);
            if (b < 0) return b;
            symbol = symbol * 2u + (unsigned)b;
            if ((b != 0) != (match_bit != 0)) break;
        } while (symbol < 0x100u);
    }
    while (symbol < 0x100u) {
        int b = bit(rc, base + symbol);
        if (b < 0) return b;
        symbol = symbol * 2u + (unsigned)b;
    }
    if (w->pos == w->size) return N10_LZMA_OUTPUT;
    w->previous = (uint8_t)symbol;
    w->data[w->pos++] = w->previous;
    w->state = w->state < 4 ? 0 : w->state < 10 ? w->state - 3 : w->state - 6;
    return 0;
}

#define READ_BIT(index) do { b = bit(rc, (index)); if (b < 0) return b; } while (0)
static int match(struct rc *rc, struct writer *w, uint32_t pos_state)
{
    size_t prob, prob_len;
    unsigned levels;
    uint32_t offset, len;
    int b, status;
    READ_BIT(LZMA_IS_REP + w->state);
    if (!b) {
        w->rep[3] = w->rep[2]; w->rep[2] = w->rep[1]; w->rep[1] = w->rep[0];
        w->state = w->state < 7 ? 0 : 3;
        prob = LZMA_LEN_CODER;
    } else {
        READ_BIT(LZMA_IS_REP_G0 + w->state);
        if (!b) {
            READ_BIT(LZMA_IS_REP_0_LONG + (w->state << 4) + pos_state);
            if (!b) {
                w->state = w->state < 7 ? 9 : 11;
                return copy_match(w, w->rep[0], 1);
            }
        } else {
            uint32_t distance;
            READ_BIT(LZMA_IS_REP_G1 + w->state);
            if (!b) distance = w->rep[1];
            else {
                READ_BIT(LZMA_IS_REP_G2 + w->state);
                if (!b) distance = w->rep[2];
                else { distance = w->rep[3]; w->rep[3] = w->rep[2]; }
                w->rep[2] = w->rep[1];
            }
            w->rep[1] = w->rep[0]; w->rep[0] = distance;
        }
        w->state = w->state < 7 ? 8 : 11;
        prob = LZMA_REP_LEN_CODER;
    }
    READ_BIT(prob + LZMA_LEN_CHOICE);
    if (!b) { prob_len = prob + LZMA_LEN_LOW + (pos_state << 3); offset = 0; levels = 3; }
    else {
        READ_BIT(prob + LZMA_LEN_CHOICE_2);
        if (!b) { prob_len = prob + LZMA_LEN_MID + (pos_state << 3); offset = 8; levels = 3; }
        else { prob_len = prob + LZMA_LEN_HIGH; offset = 16; levels = 8; }
    }
    status = tree(rc, prob_len, levels, &len);
    if (status) return status;
    len += offset;
    if (w->state < 4) {
        uint32_t slot;
        w->state += 7;
        status = tree(rc, LZMA_POS_SLOT + ((len < 4 ? len : 3) << 6), 6, &slot);
        if (status) return status;
        if (slot >= 4) {
            unsigned bits = (slot >> 1) - 1;
            uint32_t symbol = 1, mask = 1;
            w->rep[0] = 2u | (slot & 1u);
            if (slot < 14) {
                w->rep[0] <<= bits;
                prob = LZMA_SPEC_POS + w->rep[0] - slot - 1u;
            } else {
                unsigned n = bits - 4;
                while (n--) {
                    b = direct_bit(rc);
                    if (b < 0) return b;
                    w->rep[0] = (w->rep[0] << 1) | (unsigned)b;
                }
                prob = LZMA_ALIGN;
                w->rep[0] <<= 4; bits = 4;
            }
            while (bits--) {
                READ_BIT(prob + symbol);
                symbol = symbol * 2u + (unsigned)b;
                if (b) w->rep[0] |= mask;
                mask <<= 1;
            }
        } else w->rep[0] = slot;
        if (++w->rep[0] == 0) return N10_LZMA_EARLY_EOS;
    }
    return copy_match(w, w->rep[0], len + 2u);
}
#undef READ_BIT

static uint64_t le(const uint8_t *p, unsigned bytes)
{
    uint64_t value = 0;
    unsigned i;
    for (i = 0; i < bytes; ++i) value |= (uint64_t)p[i] << (8u * i);
    return value;
}

static int interval(const void *p, size_t bytes, uintptr_t *start, uintptr_t *end)
{
    *start = (uintptr_t)p;
    if (!p || bytes > UINTPTR_MAX - *start) return 0;
    *end = *start + bytes;
    return 1;
}

int n10_lzma_alone_decode(const uint8_t *input, size_t input_bytes, uint8_t *output,
    size_t output_capacity, void *workspace, size_t workspace_bytes, struct n10_lzma_result *result)
{
    uintptr_t starts[4], ends[4];
    struct rc rc;
    struct writer w;
    unsigned i, j;
    uint64_t expected;
    int status = N10_LZMA_ARGUMENT;
    _Static_assert(sizeof(struct n10_lzma_result) == 24, "fixed result ABI");
    if (!interval(input, input_bytes, &starts[0], &ends[0]) ||
        !interval(output, output_capacity, &starts[1], &ends[1]) ||
        !interval(workspace, workspace_bytes, &starts[2], &ends[2]) ||
        !interval(result, sizeof(*result), &starts[3], &ends[3])) return status;
    for (i = 0; i < 4; ++i)
        for (j = i + 1; j < 4; ++j)
            if (starts[i] < ends[j] && starts[j] < ends[i]) return status;
    result->version = 1; result->status = status; result->consumed = result->written = 0;
    if (workspace_bytes < N10_LZMA_WORKSPACE || starts[2] % _Alignof(uint16_t)) {
        result->status = N10_LZMA_WORK; return result->status;
    }
    if (input_bytes < 18 || input_bytes > N10_LZMA_MAX_BYTES) {
        result->status = N10_LZMA_INPUT; return result->status;
    }
    expected = le(input + 5, 8);
    if (input[0] != 0x5d || le(input + 1, 4) != (1u << 23) ||
        !expected || expected > N10_LZMA_MAX_BYTES || input[13] != 0) {
        result->status = N10_LZMA_HEADER; return result->status;
    }
    if (expected > output_capacity || output_capacity > N10_LZMA_MAX_BYTES) {
        result->status = N10_LZMA_OUTPUT; return result->status;
    }
    rc.input = input; rc.size = input_bytes; rc.pos = 13;
    rc.code = 0; rc.range = UINT32_MAX; rc.p = (uint16_t *)workspace;
    for (i = 0; i < 5; ++i) rc.code = (rc.code << 8) | input[rc.pos++];
    for (i = 0; i < N10_LZMA_WORKSPACE / sizeof(uint16_t); ++i) rc.p[i] = 1024;
    w.data = output; w.pos = 0; w.size = (size_t)expected; w.state = 0; w.previous = 0;
    for (i = 0; i < 4; ++i) w.rep[i] = 1;
    status = 0;
    while (w.pos < w.size) {
        uint32_t pos_state = (uint32_t)(w.pos & 3u);
        int b = bit(&rc, LZMA_IS_MATCH + (w.state << 4) + pos_state);
        if (b < 0) { status = b; break; }
        status = b ? match(&rc, &w, pos_state) : literal(&rc, &w);
        if (status) break;
    }
    result->status = status; result->consumed = rc.pos; result->written = w.pos;
    return status;
}
