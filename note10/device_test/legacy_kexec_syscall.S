/* SPDX-License-Identifier: GPL-2.0-only */
#include <asm/unistd.h>
.text
.global _start
_start:
    bl n10_legacy_init
1:  mov x0,xzr
    mov x1,xzr
    mov x2,xzr
    mov x3,xzr
    mov x4,#8
    mov x8,#__NR_ppoll
    svc #0
    b 1b
.global n10_syscall6
n10_syscall6:
    mov x8,x0
    mov x0,x1
    mov x1,x2
    mov x2,x3
    mov x3,x4
    mov x4,x5
    mov x5,x6
    svc #0
    ret
.section .note.GNU-stack,"",%progbits
