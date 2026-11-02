/* SPDX-License-Identifier: GPL-2.0-only */
/* PC-only candidate: native reserve-only early, ordinary data writes late. */
#include "carrier_lzma.h"
#ifndef N10_DATA_HOST_TEST
#include <linux/memblock.h>
#include <asm/memory.h>
#define n10_owned_reserve(n,a) __memblock_alloc_base((n),(a),MEMBLOCK_ALLOC_ACCESSIBLE)
#define n10_owned_va(p) ((unsigned long)__va(p))
#define n10_owned_pa(p) __pa(p)
#define n10_owned_linear(p) __is_lm_address(p)
#endif
#ifndef N10_OWNED_BYTES
#define N10_OWNED_BYTES 19546112u
#endif
#define N10_OWNED_ALIGN 16384u
static struct {
    unsigned char *output;
    uint64_t physical;
    unsigned int capacity, attempts, status;
} n10_owned __used;
enum { N10_OWNED_EMPTY, N10_OWNED_READY, N10_OWNED_FAILED, N10_OWNED_REPEAT };
void __init n10_owned_capture(void);
void __init n10_owned_capture(void)
{
    uint64_t physical;
    unsigned long start, last;
    if (n10_owned.attempts++) { n10_owned.status=N10_OWNED_REPEAT; return; }
    n10_owned.status=N10_OWNED_FAILED;
    physical=n10_owned_reserve(N10_OWNED_BYTES,N10_OWNED_ALIGN);
    if (!physical || physical%N10_OWNED_ALIGN || physical>UINT64_MAX-N10_OWNED_BYTES) return;
    start=n10_owned_va(physical); last=n10_owned_va(physical+N10_OWNED_BYTES-1);
    if (start>~0UL-(N10_OWNED_BYTES-1) || last!=start+N10_OWNED_BYTES-1 ||
        !n10_owned_linear(start) || !n10_owned_linear(last) ||
        n10_owned_pa(start)!=physical || n10_owned_pa(last)!=physical+N10_OWNED_BYTES-1) return;
    n10_owned.output=(unsigned char *)start;
    n10_owned.physical=physical; n10_owned.capacity=N10_OWNED_BYTES;
    n10_owned.status=N10_OWNED_READY;
}
