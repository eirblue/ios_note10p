/* Post-shutdown ARM64 entry adapter prototype. Not a Linux/Android boot image.
 * Caller must already have stopped other CPUs/devices and cleaned caches.
 * Requires writable PC-relative record and accessible prepared boot_args.
 * Does not disable an active MMU, flush caches, initialize GIC or reserve RAM.
 */
.section .text.entry,"ax"
.balign 4
.global _start
.type _start,%function
_start:
    adr x4, n10_transfer_record
    str xzr, [x4, #48]
    str xzr, [x4, #56]
    mrs x5, CurrentEL
    cmp x5, #4
    b.ne .Lbad_el
    msr DAIFSet, #15
    mrs x5, SCTLR_EL1
    str x5, [x4, #56]
    /* Reject active MMU, data cache or instruction cache. A cleared C bit
     * alone does not prove earlier dirty lines were cleaned by the caller. */
    mov x6, #0x1005
    tst x5, x6
    b.ne .Lbad_state
    ldr x5, [x4]
    adr x6, .Lmagic
    ldr x6, [x6]
    cmp x5, x6
    b.ne .Lbad_record
    ldp w5, w6, [x4, #8]
    cmp w5, #1
    b.ne .Lbad_record
    cmp w6, #64
    b.ne .Lbad_record
    ldp x5, x6, [x4, #32]
    orr x5, x5, x6
    cbnz x5, .Lbad_record
    ldp x0, x17, [x4, #16]
    cbz x0, .Lbad_record
    cbz x17, .Lbad_record
    tst x0, #0x3fff
    b.ne .Lbad_record
    tst x17, #3
    b.ne .Lbad_record
    /* This prototype accepts only physical addresses below 2^48. */
    orr x5, x0, x17
    lsr x5, x5, #48
    cbnz x5, .Lbad_record
    mov x5, #1
    str x5, [x4, #48]
    dsb sy
    mov x1, xzr
    mov x2, xzr
    mov x3, xzr
    br x17
.Lbad_el:
    mov x5, #2
    b .Lfail
.Lbad_record:
    mov x5, #3
    b .Lfail
.Lbad_state:
    mov x5, #4
.Lfail:
    str x5, [x4, #48]
    dsb sy
.global n10_transfer_halt
n10_transfer_halt:
    wfe
    b n10_transfer_halt
.balign 8
.Lmagic:
    .ascii "N10XFER1"
.size _start, . - _start

.section .data.record,"aw"
.balign 64
.global n10_transfer_record
n10_transfer_record:
    .ascii "N10XFER1"
    .word 1, 64
    .quad 0 /* prepared boot_args physical address; zero refuses transfer */
    .quad 0 /* actual XNU entry physical address; zero refuses transfer */
    .quad 0 /* flags: all currently unsupported */
    .quad 0 /* reserved */
    .quad 0 /* status: 1=branch attempted, 2=EL, 3=record, 4=SCTLR refusal */
    .quad 0 /* observed SCTLR_EL1, when entered at EL1 */
