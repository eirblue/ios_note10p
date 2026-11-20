/* SPDX-License-Identifier: GPL-2.0-only */
/* Physical diagnostic ABI witness with v305 boot_args field checks. No stack, external call or device access. */
#include <linux/linkage.h>
#include "n304_abi_contract.h"

.macro n304_fnv
    mov w11, #0x9dc5
    movk w11, #0x811c, lsl #16
    mov w12, #0x193
    movk w12, #0x100, lsl #16
.Lhash\@:
    ldrb w9, [x7], #1
    eor w11, w11, w9
    mul w11, w11, w12
    subs x8, x8, #1
    b.ne .Lhash\@
.endm

.macro n304_hex reg, offset, shift
    add x7, x3, #\offset
    mov x8, #\shift
.Lhex\@:
    lsr x9, \reg, x8
    and w9, w9, #15
    add w10, w9, #'0'
    add w12, w10, #39
    cmp w9, #9
    csel w10, w12, w10, hi
    strb w10, [x7], #1
    subs x8, x8, #4
    b.pl .Lhex\@
.endm

.pushsection .idmap.text,"awx"
.balign 4
ENTRY(n304_post_abi)
    mov x19, x0
    mov x20, x1
    mov x21, x2
    mov x22, x3
    mrs x9, CurrentEL
    cmp x9, #4
    b.ne .Lpark
    ubfx x13, x9, #2, #2            /* EL 관측값 */
    mrs x9, daif
    ubfx x14, x9, #6, #4            /* D,A,I,F = bits 9..6 */
    cmp x14, #0xf
    b.ne .Lpark
    mrs x23, sctlr_el1
    mov x12, #0x1005
    tst x23, x12
    b.ne .Lpark
    orr x9, x20, x21                /* x1,x2는 0, x3는 관측용 */
    cbnz x9, .Lpark
    cmp x19, #0
    b.eq .Lpark
    tst x19, #(N304_ARENA_BYTES - 1)
    b.ne .Lpark
    add x24, x19, #N304_META_OFFSET
    ldr x9, [x24, #N304_SELF]
    cmp x9, x19
    b.ne .Lpark
    ldr w25, [x24, #N304_ADT_BYTES]
    cmp w25, #N304_ADT_MIN_BYTES
    b.lo .Lpark
    cmp w25, #N304_ADT_MAX_BYTES
    b.hi .Lpark
    ldrh w9, [x19]
    cmp w9, #2
    b.ne .Lpark
    ldrh w9, [x19, #2]
    cmp w9, #2
    b.ne .Lpark
    add x10, x19, #N304_ADT_OFFSET
    ldr x9, [x19, #96]
    cmp x9, x10
    b.ne .Lpark
    ldr w9, [x19, #104]
    cmp w9, w25
    b.ne .Lpark
    /* v305: XNU-consumed boot_args scalars and a printable NUL-terminated CommandLine. */
    ldp x9, x10, [x19, #N305_VIRT]  /* virtBase, physBase */
    cmp x9, x19
    ccmp x10, x19, #0, eq
    b.ne .Lpark
    ldp x9, x10, [x19, #N305_MEMSIZE] /* memSize, topOfKernelData */
    sub x10, x10, x19
    cmp x9, #N304_ARENA_BYTES
    ccmp x10, x9, #0, eq
    b.ne .Lpark
    ldr w9, [x19, #N305_MACHINE]
    cbnz w9, .Lpark
    add x7, x19, #N305_BOOTFLAGS
    ldp x9, x10, [x7]               /* bootFlags, memSizeActual */
    cbnz x9, .Lpark
    cmp x10, #N304_ARENA_BYTES
    b.lo .Lpark
    ldrb w9, [x19, #N305_CMDLINE]
    cbz w9, .Lpark
    add x7, x19, #N305_CMDLINE
    mov x8, #N305_CMDLINE_BYTES
.Lcmd:
    ldrb w9, [x7], #1
    cbz w9, .Lcmd_ok
    sub w10, w9, #32                /* printable 32..126 */
    cmp w10, #94
    b.hi .Lpark
    subs x8, x8, #1
    b.ne .Lcmd
    b .Lpark
.Lcmd_ok:
    mov x7, x19
    mov x8, #N304_ARGS_BYTES
    n304_fnv
    ldr w9, [x24, #N304_ARGS_HASH]
    cmp w11, w9
    b.ne .Lpark
    mov w26, w11
    add x7, x19, #N304_ADT_OFFSET
    mov x8, x25
    n304_fnv
    ldr w9, [x24, #N304_ADT_HASH]
    cmp w11, w9
    b.ne .Lpark
    mov w27, w11
    ldp x3, x4, [x24, #N304_RECORD]
    ldr x5, [x24, #N304_NEXT]
    add x1, x19, #N304_ARENA_BYTES
    add x0, x3, #N304_RECORD_BYTES
    cmp x0, x3
    b.ls .Lpark
    add x2, x4, #4
    cmp x2, x4
    b.ls .Lpark
    tst x4, #3
    b.ne .Lpark
    cmp x3, x1                      /* 기록 vs 인자 영역 */
    b.hs .Lrec_ok
    cmp x0, x19
    b.hi .Lpark
.Lrec_ok:
    cmp x4, x1                      /* 커서 vs 인자 영역 */
    b.hs .Lcur_ok
    cmp x2, x19
    b.hi .Lpark
.Lcur_ok:
    cmp x3, x2                      /* 기록 vs 커서 */
    b.hs .Lsep_ok
    cmp x4, x0
    b.lo .Lpark
.Lsep_ok:
    add x7, x24, #N304_TEXT
    mov x8, #0
.Lcopy:
    ldrb w9, [x7, x8]
    strb w9, [x3, x8]
    add x8, x8, #1
    cmp x8, #N304_RECORD_BYTES
    b.lo .Lcopy
    n304_hex x19, N304_REG_OFFSET, 60
    n304_hex x20, (N304_REG_OFFSET + 17), 60
    n304_hex x21, (N304_REG_OFFSET + 34), 60
    n304_hex x22, (N304_REG_OFFSET + 51), 60
    n304_hex x26, N304_ARGS_HASH_OFFSET, 28
    n304_hex x27, N304_ADT_HASH_OFFSET, 28
    n304_hex x25, N304_ADT_LENGTH_OFFSET, 4
    n304_hex x23, N304_SCTLR_OFFSET, 60
    add w9, w13, #48                /* EL is 0..3: ASCII '0'+EL */
    strb w9, [x3, #N304_EL_OFFSET]
    add w9, w14, #87                /* DAIF nibble is exactly 0xf here: ASCII 'f' */
    strb w9, [x3, #N304_DAIF_OFFSET]
    add x7, x3, #N304_BODY_OFFSET
    mov x8, #N304_BODY_BYTES
    n304_fnv
    n304_hex x11, N304_CSUM_OFFSET, 28
    dsb sy
    mov w9, #'T'
    strb w9, [x3, #N304_COMMIT_OFFSET]
    dsb sy
    str w5, [x4]                    /* 커밋 후 커서 전진 */
    dsb sy
.Lpark:
    yield
    b .Lpark
ENDPROC(n304_post_abi)
.popsection
