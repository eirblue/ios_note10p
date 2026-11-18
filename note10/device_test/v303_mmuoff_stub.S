/* Physical-only post-transition witness; no stack, literal pool, calls or MMIO. */
#include <linux/linkage.h>
#include <linux/n303_mmuoff_contract.h>
.pushsection .idmap.text,"awx"
.balign 4
ENTRY(n303_post_mmu)
    mrs x10, CurrentEL
    cmp x10, #4
    b.ne .Lpark
    mrs x11, sctlr_el1
    mov x12, #0x1005
    tst x11, x12
    b.ne .Lpark
    ldr x3, [x0]
    ldr x4, [x0, #8]
    ldr x5, [x0, #16]
    ldr x6, [x0, #24]
    cmp x6, #N303_RECORD_BYTES
    b.ne .Lpark
    add x7, x0, #N303_PARAM_TEXT
    mov x8, #0
.Lcopy:
    ldrb w9, [x7, x8]
    strb w9, [x3, x8]
    add x8, x8, #1
    cmp x8, x6
    b.lo .Lcopy
    mov w9, #'1'
    strb w9, [x3, #N303_EL_OFFSET]
    add x7, x3, #N303_SCTLR_OFFSET
    mov x8, #60
.Lsctlr:
    lsr x9, x11, x8
    and w9, w9, #15
    add w10, w9, #'0'
    add w12, w10, #39
    cmp w9, #9
    csel w10, w12, w10, hi
    strb w10, [x7], #1
    subs x8, x8, #4
    b.pl .Lsctlr
    mov w11, #0x9dc5
    movk w11, #0x811c, lsl #16
    mov w12, #0x193
    movk w12, #0x100, lsl #16
    add x7, x3, #N303_BODY_OFFSET
    mov x8, #N303_BODY_BYTES
.Lhash:
    ldrb w9, [x7], #1
    eor w11, w11, w9
    mul w11, w11, w12
    subs x8, x8, #1
    b.ne .Lhash
    add x7, x3, #N303_CHECKSUM_OFFSET
    mov x8, #28
.Lchecksum:
    lsr w9, w11, w8
    and w9, w9, #15
    add w10, w9, #'0'
    add w12, w10, #39
    cmp w9, #9
    csel w10, w12, w10, hi
    strb w10, [x7], #1
    subs x8, x8, #4
    b.pl .Lchecksum
    dsb sy
    str w5, [x4]
    dsb sy
    /* Commit last: even a full-ring recovery copy cannot accept a pending line. */
    mov w9, #'T'
    strb w9, [x3, #N303_COMMIT_OFFSET]
    dsb sy
.Lpark:
    yield
    b .Lpark
ENDPROC(n303_post_mmu)
.popsection
