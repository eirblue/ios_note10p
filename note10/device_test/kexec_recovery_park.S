/* SPDX-License-Identifier: GPL-2.0-only */
/* Physical proof payload only. No XNU, MMIO, stack, petting or disarming. */
.section .text,"ax"
.balign 4
.global _start
_start:
    msr DAIFSet, #15
    adr x4, n10_park_record
    mov x5, #1
    str x5, [x4, #8] /* Owned segment breadcrumb; persistence is NOT assumed. */
    dsb sy
1:  wfi
    b 1b
.balign 64
.global n10_park_record
n10_park_record:
    .ascii "N10PARK1"
    .quad 0
.global n10_park_cookie
n10_park_cookie:
    .space 16
.section .note.GNU-stack,"",%progbits
