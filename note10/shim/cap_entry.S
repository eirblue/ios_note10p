/* Single-CPU privileged diagnostic entry, NOT an Android boot image.
 * Requires its loaded record to be writable and AArch64 EL1 or EL2 entry.
 * No stack, MMIO, cache maintenance, MMU setup, CPU startup or OS launch.
 */
#include "cap_record.h"
.section .text.entry,"ax"
.balign 4
.global _start
.type _start,%function
_start:
    adr x4, n10_cap_record
    mov x5, #N10_CAP_STATUS
0:
    str xzr, [x4, x5]
    add x5, x5, #8
    cmp x5, #N10_CAP_SIZE
    b.lo 0b
    stp x0, x1, [x4, #N10_CAP_X0]
    stp x2, x3, [x4, #(N10_CAP_X0 + 16)]
    mov x5, sp
    str x5, [x4, #N10_CAP_SP]
    mrs x5, CurrentEL
    str x5, [x4, #N10_CAP_EL]
    mrs x6, DAIF
    str x6, [x4, #N10_CAP_DAIF]
    cmp x5, #4
    b.eq 1f
    cmp x5, #8
    b.eq 1f
    mov x5, #2
    b 5f
1:
    msr DAIFSet, #15
.macro capture reg, offset
    mrs x5, \reg
    str x5, [x4, #\offset]
.endm
    capture MPIDR_EL1, N10_CAP_MPIDR
    capture CNTFRQ_EL0, N10_CAP_CNTFRQ
    capture ID_AA64MMFR0_EL1, N10_CAP_MMFR0
    capture ID_AA64MMFR1_EL1, N10_CAP_MMFR1
    capture ID_AA64ISAR0_EL1, N10_CAP_ISAR0
    capture ID_AA64ISAR1_EL1, N10_CAP_ISAR1
    capture ID_AA64PFR0_EL1, N10_CAP_PFR0
    capture CTR_EL0, N10_CAP_CTR
    capture CLIDR_EL1, N10_CAP_CLIDR
    capture SCTLR_EL1, N10_CAP_SCTLR1
    capture TCR_EL1, N10_CAP_TCR1
    capture TTBR0_EL1, N10_CAP_TTBR01
    capture TTBR1_EL1, N10_CAP_TTBR11
    capture VBAR_EL1, N10_CAP_VBAR1
    ldr x5, [x4, #N10_CAP_EL]
    cmp x5, #8
    b.ne 2f
    capture SCTLR_EL2, N10_CAP_SCTLR2
    capture TCR_EL2, N10_CAP_TCR2
    capture HCR_EL2, N10_CAP_HCR2
2:
    mrs x8, CSSELR_EL1
    str x8, [x4, #N10_CAP_CSSELR]
    ldr x7, [x4, #N10_CAP_CLIDR]
    mov x6, #0
    add x9, x4, #N10_CAP_CCSIDR
3:
    /* Probe only CLIDR-declared data/separate/unified cache levels. */
    add x10, x6, x6, lsl #1
    lsr x11, x7, x10
    and x11, x11, #7
    cmp x11, #2
    b.lo 4f
    cmp x11, #4
    b.hi 4f
    lsl x10, x6, #1
    msr CSSELR_EL1, x10
    isb
    mrs x5, CCSIDR_EL1
    str x5, [x9, x6, lsl #3]
4:
    add x6, x6, #1
    cmp x6, #7
    b.lo 3b
    msr CSSELR_EL1, x8
    isb
    mov x5, #1
5:
    dsb sy
    str x5, [x4, #N10_CAP_STATUS]
    dsb sy
.global n10_cap_halt
n10_cap_halt:
    wfe
    b n10_cap_halt
.size _start,.-_start

.section .data.record,"aw"
.balign 64
.global n10_cap_record
n10_cap_record:
    .ascii "N10CAP01"
    .long 1
    .long N10_CAP_SIZE
    .zero N10_CAP_SIZE - 16
.size n10_cap_record,.-n10_cap_record
