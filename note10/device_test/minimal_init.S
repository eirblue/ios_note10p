/* SPDX-License-Identifier: MIT
 * PID1 for a future manual RAM-reservation diagnostic. No filesystem mounts,
 * block access, reboot, module loading or handoff. Linux UAPI supplies syscall
 * numbers; this is an ordinary static Linux userspace program, not XNU.
 */
#include <asm/unistd.h>
.section .text,"ax"
.global _start
.type _start,%function
_start:
    mov x0, #1
    adr x1, .Lmessage
    mov x2, #(.Lmessage_end - .Lmessage)
    mov x8, #__NR_write
    svc #0
.Lidle:
    mov x0, xzr
    mov x1, xzr
    mov x2, xzr
    mov x3, xzr
    mov x4, #8
    mov x8, #__NR_ppoll
    svc #0
    b .Lidle
.Lmessage:
    .ascii "N10INIT1 IDLE reservation diagnostic; no Android or XNU launch\n"
.Lmessage_end:
.size _start, . - _start
.section .note.GNU-stack,"",%progbits
