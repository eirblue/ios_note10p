/* SPDX-License-Identifier: MIT
 * Static Linux PID1. Assembles a startup record from kernel identity fields,
 * writes it to kmsg,
 * then sleeps. No mount, block I/O, exec, Android, XNU or reboot syscall.
 */
#include <asm/unistd.h>
.section .text,"ax"
.global _start
.type _start,%function
_start:
    ldr x0, [sp]
    cmp x0, #2
    b.ne .Lidle
    ldr x19, [sp, #16]
    mov x20, #0
.Llength:
    cmp x20, #255
    b.hs .Lidle
    ldrb w0, [x19, x20]
    cbz w0, .Lopen
    add x20, x20, #1
    b .Llength
.Lopen:
    mov x0, #-100
    adr x1, .Lkmsg
    mov x2, #1
    mov x3, #0
    mov x8, #__NR_openat
    svc #0
    tbnz x0, #63, .Lidle
    mov x21, x0
    /* The startup tag is assembled only after PID1 has entered userspace;
     * the kernel argv contains identity fields, never a success marker. */
    sub sp, sp, #512
    mov x22, sp
    adr x23, .Lprefix
    mov x24, #(.Lprefix_end - .Lprefix)
    bl .Lcopy
    mov x23, x19
    mov x24, x20
    bl .Lcopy
    adr x23, .Lsuffix
    mov x24, #(.Lsuffix_end - .Lsuffix)
    bl .Lcopy
    mov x0, x21
    mov x1, sp
    sub x2, x22, x1
    mov x8, #__NR_write
    svc #0
    add sp, sp, #512
    mov x0, x21
    mov x8, #__NR_close
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
.Lcopy:
    cbz x24, .Lcopied
    ldrb w0, [x23], #1
    strb w0, [x22], #1
    sub x24, x24, #1
    b .Lcopy
.Lcopied:
    ret
.Lprefix:
    .ascii "<6>N10INIT2 "
.Lprefix_end:
.Lsuffix:
    .ascii " started=1\n"
.Lsuffix_end:
.Lkmsg:
    .asciz "/dev/kmsg"
    .asciz "N10MININIT2 Linux PID1; no Android or XNU launch"
.size _start, . - _start
.section .note.GNU-stack,"",%progbits
