/* SPDX-License-Identifier: BSD-2-Clause */
/* x0=VA,x1=PA,x2=bytes,x3=poolPA,x4=capacity; x0=status,x1=used.
 * x18-x30/SP preserved. No target-memory reads, stack, BL or sysreg access.
 */
#include "exynos_leaf_mapper.h"
#ifdef N10_MAPPER_FIXTURE
#define EXT(x) _##x
#define LEXT(x) _##x:
#endif
.text
.p2align 2
.globl EXT(n10_exynos_bootstrap_map)
LEXT(n10_exynos_bootstrap_map)
    /* Preserve inputs in caller-clobbered registers. */
    mov x5,x0
    mov x6,x1
    mov x7,x2
    mov x8,x3
    mov x9,x4
    cbz x7,.Ln10_args
    mov x10,#N10_MAP_MAX_BYTES
    cmp x7,x10
    b.hi .Ln10_args
    orr x10,x5,x6
    orr x10,x10,x7
    orr x10,x10,x8
    tst x10,#(N10_MAP_PAGE-1)
    b.ne .Ln10_args
    mov x10,#N10_MAP_POOL_PAGES
    lsl x10,x10,#14
    cmp x9,x10
    b.ne .Ln10_capacity
    /* Physical end and canonical high VA last byte; no wrapping. */
    adds x11,x6,x7
    b.cs .Ln10_range
    mov x10,#N10_MAP_PA_LIMIT
    cmp x11,x10
    b.hi .Ln10_range
    lsr x10,x5,#47
    mov x12,#0x1ffff
    cmp x10,x12
    b.ne .Ln10_range
    adds x12,x5,x7
    b.cs .Ln10_range
    sub x12,x12,#1
    lsr x10,x12,#47
    mov x13,#0x1ffff
    cmp x10,x13
    b.ne .Ln10_range
    /* Designated writable pool wholly inside owned physical extent. */
    cmp x8,x6
    b.lo .Ln10_pool
    adds x10,x8,x9
    b.cs .Ln10_pool
    cmp x10,x11
    b.hi .Ln10_pool
    /* Exact preflight table count for BOTH independent regimes. */
    sub x10,x7,#1
    and x11,x5,#0xfffffffff
    add x11,x11,x10
    lsr x11,x11,#36
    add x11,x11,#1
    and x12,x5,#0x1ffffff
    add x12,x12,x10
    lsr x12,x12,#25
    add x11,x11,x12
    add x11,x11,#1
    and x12,x6,#0xfffffffff
    add x12,x12,x10
    lsr x12,x12,#36
    add x11,x11,x12
    add x11,x11,#1
    and x12,x6,#0x1ffffff
    add x12,x12,x10
    lsr x12,x12,#25
    add x12,x12,#1  /* physical L3 table count */
    add x11,x11,x12
    add x11,x11,#2  /* two independent L1 roots */
    lsl x11,x11,#14
    cmp x11,x9
    b.hi .Ln10_capacity
    /* First store only after ALL validation/preflight. */
    mov x0,x8
    lsr x1,x9,#4
.Ln10_zero:
    stp xzr,xzr,[x0],#16
    subs x1,x1,#1
    b.ne .Ln10_zero
    add x10,x8,#8,lsl #12 /* free cursor after two16KiB roots */
    mov x11,x8
    mov x12,x6
    mov x13,x6
    lsr x14,x7,#14
    mov x15,#0
.Ln10_page:
    ubfx x16,x12,#36,#11
    add x16,x11,x16,lsl #3
    ldr x17,[x16]
    cbnz x17,.Ln10_have_l2
    mov x0,x10
    add x10,x10,#4,lsl #12
    orr x17,x0,#N10_MAP_TABLE_ATTR
    str x17,[x16]
    b .Ln10_l2
.Ln10_have_l2:
    and x0,x17,#0x0000ffffffffc000
.Ln10_l2:
    ubfx x16,x12,#25,#11
    add x16,x0,x16,lsl #3
    ldr x17,[x16]
    cbnz x17,.Ln10_have_l3
    mov x0,x10
    add x10,x10,#4,lsl #12
    orr x17,x0,#N10_MAP_TABLE_ATTR
    str x17,[x16]
    b .Ln10_l3
.Ln10_have_l3:
    and x0,x17,#0x0000ffffffffc000
.Ln10_l3:
    ubfx x16,x12,#14,#11
    add x16,x0,x16,lsl #3
    movz x17,#0x0603
    movk x17,#0x0040,lsl #48
    orr x17,x13,x17
    str x17,[x16]
    add x12,x12,#4,lsl #12
    add x13,x13,#4,lsl #12
    subs x14,x14,#1
    b.ne .Ln10_page
    cbnz x15,.Ln10_done
    mov x15,#1
    add x11,x8,#4,lsl #12
    mov x12,x5
    mov x13,x6
    lsr x14,x7,#14
    b .Ln10_page
.Ln10_done:
    sub x1,x10,x8
    mov x0,#0
    ret
.Ln10_args:
    mov x0,#1
    b .Ln10_refused
.Ln10_range:
    mov x0,#2
    b .Ln10_refused
.Ln10_pool:
    mov x0,#3
    b .Ln10_refused
.Ln10_capacity:
    mov x0,#4
.Ln10_refused:
    mov x1,#0
    ret
