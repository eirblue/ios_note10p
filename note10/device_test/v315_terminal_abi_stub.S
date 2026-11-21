/* SPDX-License-Identifier: GPL-2.0-only */
/* Physical diagnostic ABI witness: v305 boot_args field checks, the v306 cpu0 ADT walk and MPIDR/CNTFRQ
 * cross-checks, v307 memory-map and CNTVCT checks, the v309 /chosen dram-base/dram-size span check, plus the
 * v310 root-level /defaults{name="defaults"} node check, and the v311 window/boot_args geometry and loaded XNU image
 * checks (Mach-O header and word-FNV of the whole image, read-only; the image is never executed), and the v312 entry
 * target: the Linux-parsed LC_UNIXTHREAD entry_offset is bounded and the 32-bit word at the entry is loaded and recorded
 * in r[3]. v313: three pre-branch gates (the entry word is an unconditional B, CPU0 supports the 16 KiB granule
 * (ID_AA64MMFR0_EL1.TGran16 1 or 2), window end < 2^39), dc civac of the record/cursor lines, then the N313PS2T commit and
 * cursor advance, after which the entry is branched to exactly once: 'isb; mov x0, x19; br x18' with
 * x18 = B + N311_KERNEL_OFFSET + entry_offset (x0 = boot_args = B). Every gate failure parks without a record.
 * v314: Block B cleans the record + XNU breadcrumb span [x3, x3 + N314_RECORD_SPAN) (the private XNU patch writes the two
 * 8-byte breadcrumbs right after the record); the separation check and the copy stay at N304_RECORD_BYTES.
 * v315: the clean span is N315_RECORD_SPAN (record + three 8-byte XNU checkpoint crumbs), and boot_args memSize and the
 * image end are checked against N315_BOOT_MEMSIZE (N311_KERNEL_OFFSET + 32 MiB) in x8 instead of the window size.
 * No stack, call, device access or sysreg write; x18 has exactly one writer (Block A) and one reader (the br). */
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
    isb
    mrs x28, cntvct_el0             /* v307: entry counter */
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
    orr x9, x20, x21                /* x1,x2는 0, x3는 미검사 (x22: v309 dram-size, v312부터 r[3] entry 값) */
    cbnz x9, .Lpark
    cmp x19, #0
    b.eq .Lpark
    tst x19, #(N311_WINDOW_ALIGN - 1)  /* v311: window base B */
    b.ne .Lpark
    add x24, x19, #N304_META_OFFSET
    ldr x9, [x24, #N304_SELF]
    cmp x9, x19
    b.ne .Lpark
    ldr w25, [x24, #N304_ADT_BYTES]
    cmp w25, #N306_ADT_MIN_BYTES
    b.lo .Lpark
    cmp w25, #N307_ADT_MAX_BYTES
    b.hi .Lpark
    tst w25, #3
    b.ne .Lpark
    ldrh w9, [x19]
    cmp w9, #2
    b.ne .Lpark
    ldrh w9, [x19, #2]
    cmp w9, #2
    b.ne .Lpark
    movz x11, #((N311_VIRT_BASE >> 16) & 0xffff), lsl #16   /* v311: x11 = virtBase */
    movk x11, #((N311_VIRT_BASE >> 32) & 0xffff), lsl #32
    movk x11, #((N311_VIRT_BASE >> 48) & 0xffff), lsl #48
    add x10, x11, #N306_ADT_OFFSET  /* deviceTreeP = virtBase + ADT offset */
    ldr x9, [x19, #96]
    cmp x9, x10
    b.ne .Lpark
    ldr w9, [x19, #104]
    cmp w9, w25
    b.ne .Lpark
    /* v305: XNU-consumed boot_args scalars and a printable NUL-terminated CommandLine. */
    ldp x9, x10, [x19, #N305_VIRT]  /* virtBase, physBase */
    cmp x9, x11
    ccmp x10, x19, #0, eq
    b.ne .Lpark
    /* v311: image_bytes nonzero, 16 KiB multiple; x12 = window size (live to memSizeActual).
     * v315: x8 = N315_BOOT_MEMSIZE (dead here: first written next by .Lcmd); image end <= x8 and memSize == x8. */
    ldr w0, [x24, #N311_META_IMAGE_BYTES]
    cbz w0, .Lpark
    tst w0, #(N304_ARENA_BYTES - 1)
    b.ne .Lpark
    movz x12, #(N311_WINDOW_BYTES >> 16), lsl #16
    movz x8, #(N315_BOOT_MEMSIZE >> 16), lsl #16
    movk x8, #(N315_BOOT_MEMSIZE & 0xffff)
    mov x1, #(N311_KERNEL_OFFSET & 0xffff)  /* 0x1004 exceeds the 12-bit add immediate */
    movk x1, #(N311_KERNEL_OFFSET >> 16), lsl #16
    add x1, x1, x0                  /* kernel offset + image_bytes */
    cmp x1, x8
    b.hi .Lpark
    add x1, x1, x19                 /* expected topOfKernelData */
    ldp x9, x10, [x19, #N305_MEMSIZE] /* memSize, topOfKernelData */
    cmp x9, x8
    ccmp x10, x1, #0, eq
    b.ne .Lpark
    ldr w9, [x19, #N305_MACHINE]
    cbnz w9, .Lpark
    add x7, x19, #N305_BOOTFLAGS
    ldp x9, x10, [x7]               /* bootFlags, memSizeActual */
    cbnz x9, .Lpark
    cmp x10, x12                    /* v311: memSizeActual >= window size */
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
    /* v306: Video[6] is zero. */
    ldp x9, x10, [x19, #N306_VIDEO]
    orr x9, x9, x10
    ldp x10, x11, [x19, #(N306_VIDEO + 16)]
    orr x9, x9, x10
    orr x9, x9, x11
    ldp x10, x11, [x19, #(N306_VIDEO + 32)]
    orr x9, x9, x10
    orr x9, x9, x11
    cbnz x9, .Lpark
    /* v306: iterative structural ADT walk; x6 base, x7 cursor, x8 pending nodes, x10 node count. */
    add x6, x19, #N306_ADT_OFFSET
    mov x7, #0
    mov x8, #1
    mov x10, #0
.Lnode:
    cbz x8, .Lwalk_end
    sub x8, x8, #1
    add x10, x10, #1
    cmp x10, #32
    b.hi .Lpark
    add x9, x7, #8
    cmp x9, x25
    b.hi .Lpark
    add x0, x6, x7
    ldp w11, w12, [x0]              /* nProps, nChildren */
    mov x7, x9
    cbz w11, .Lpark
    cmp w11, #32
    b.hi .Lpark
    cmp w12, #32
    b.hi .Lpark
    add x8, x8, x12
.Lprop:
    add x9, x7, #36
    cmp x9, x25
    b.hi .Lpark
    add x0, x6, x7
    ldrb w1, [x0]
    cbz w1, .Lpark                  /* name[0] != 0 */
    ldrb w1, [x0, #31]
    cbnz w1, .Lpark                 /* name[31] == 0 */
    ldr w1, [x0, #32]               /* full u32 length; any oversize value fails the bound */
    add x1, x1, #3
    and x1, x1, #0xfffffffffffffffc
    add x9, x9, x1
    cmp x9, x25
    b.hi .Lpark
    mov x7, x9
    subs w11, w11, #1
    b.ne .Lprop
    b .Lnode
.Lwalk_end:
    cmp x7, x25
    b.ne .Lpark
    mov x17, x10                    /* v307: walked node count for n= */
    /* v307: /chosen/memory-map values. 4-aligned u64 pairs are read as 32-bit halves (Device memory). */
    ldr w0, [x24, #N307_META_BOOTARGS_OFF]
    tst w0, #3
    b.ne .Lpark
    cmp w0, #36
    b.lo .Lpark
    add x9, x0, #16
    cmp x9, x25
    b.hi .Lpark
    add x0, x6, x0
    ldur w9, [x0, #-4]
    cmp w9, #16
    b.ne .Lpark
    ldur w9, [x0, #-36]             /* name prefix "Boot" */
    mov w10, #0x6f42
    movk w10, #0x746f, lsl #16
    cmp w9, w10
    b.ne .Lpark
    ldur w9, [x0, #-32]             /* name prefix "Args" */
    mov w10, #0x7241
    movk w10, #0x7367, lsl #16
    cmp w9, w10
    b.ne .Lpark
    ldp w9, w10, [x0]
    orr x9, x9, x10, lsl #32
    ldp w10, w11, [x0, #8]
    orr x10, x10, x11, lsl #32
    cmp x10, #N304_ARGS_BYTES
    ccmp x9, x19, #0, eq
    b.ne .Lpark
    ldr w0, [x24, #N307_META_DEVTREE_OFF]
    tst w0, #3
    b.ne .Lpark
    cmp w0, #36
    b.lo .Lpark
    add x9, x0, #16
    cmp x9, x25
    b.hi .Lpark
    add x0, x6, x0
    ldur w9, [x0, #-4]
    cmp w9, #16
    b.ne .Lpark
    ldur w9, [x0, #-36]             /* name prefix "Devi" */
    mov w10, #0x6544
    movk w10, #0x6976, lsl #16
    cmp w9, w10
    b.ne .Lpark
    ldur w9, [x0, #-32]             /* name prefix "ceTr" */
    mov w10, #0x6563
    movk w10, #0x7254, lsl #16
    cmp w9, w10
    b.ne .Lpark
    ldp w9, w10, [x0]
    orr x9, x9, x10, lsl #32
    ldp w10, w11, [x0, #8]
    orr x10, x10, x11, lsl #32
    cmp x9, x6                      /* x6 = x19 + N306_ADT_OFFSET */
    ccmp x10, x25, #0, eq
    b.ne .Lpark
    /* v309: /chosen dram-base and dram-size (LE64, 32-bit halves); [x19, x19 + arena) inside [base, base + size). */
    ldr w0, [x24, #N309_META_DRAM_OFF]
    tst w0, #3
    b.ne .Lpark
    cmp w0, #36
    b.lo .Lpark
    add x9, x0, #(N309_DRAM_NAME_STRIDE + 8)   /* base value, size header and size value */
    cmp x9, x25
    b.hi .Lpark
    add x0, x6, x0
    ldur w9, [x0, #-4]
    cmp w9, #8
    b.ne .Lpark
    ldur w9, [x0, #-36]             /* name prefix "dram" */
    mov w10, #0x7264
    movk w10, #0x6d61, lsl #16
    cmp w9, w10
    b.ne .Lpark
    ldur w9, [x0, #-32]             /* name prefix "-bas" */
    mov w11, #0x622d
    movk w11, #0x7361, lsl #16
    cmp w9, w11
    b.ne .Lpark
    ldr w9, [x0, #(N309_DRAM_NAME_STRIDE - 4)]
    cmp w9, #8
    b.ne .Lpark
    ldr w9, [x0, #8]                /* name prefix "dram" */
    cmp w9, w10
    b.ne .Lpark
    ldr w9, [x0, #12]               /* name prefix "-siz" */
    mov w11, #0x732d
    movk w11, #0x7a69, lsl #16
    cmp w9, w11
    b.ne .Lpark
    ldp w9, w10, [x0]
    orr x9, x9, x10, lsl #32        /* dram-base */
    ldp w10, w11, [x0, #N309_DRAM_NAME_STRIDE]
    orr x22, x10, x11, lsl #32      /* dram-size; only for the containment check below (v312: r[3] reuses x22) */
    cbz x22, .Lpark
    adds x10, x9, x22
    b.cs .Lpark
    cmp x9, x19
    b.hi .Lpark
    mov x11, #N311_WINDOW_BYTES     /* v311: whole window inside DRAM (x12 was clobbered by the walk) */
    adds x11, x19, x11
    b.cs .Lpark
    cmp x11, x10
    b.hi .Lpark
    /* v310: root nChildren 3 and /defaults{name="defaults"} (nProps 1, nChildren 0) ending exactly at adt_bytes.
     * Scratch w0, w9-w11 only. */
    ldr w9, [x6, #4]                /* root nChildren */
    cmp w9, #3
    b.ne .Lpark
    ldr w0, [x24, #N310_META_DEFAULTS_OFF]
    add x9, x0, #N310_DEFAULTS_NODE_BYTES
    cmp x9, x25                     /* node ends at adt_bytes; bounds every read below */
    b.ne .Lpark
    tst w0, #3
    b.ne .Lpark
    add x0, x6, x0
    ldp w9, w10, [x0]               /* nProps, nChildren */
    cmp w9, #1
    ccmp w10, #0, #0, eq
    b.ne .Lpark
    ldp w9, w10, [x0, #8]           /* key "name", then a zero word */
    mov w11, #0x616e
    movk w11, #0x656d, lsl #16
    cmp w9, w11
    ccmp w10, #0, #0, eq
    b.ne .Lpark
    ldr w9, [x0, #40]               /* length 9 */
    cmp w9, #9
    b.ne .Lpark
    ldp w9, w10, [x0, #44]          /* value "defa", "ults" */
    mov w11, #0x6564
    movk w11, #0x6166, lsl #16
    cmp w9, w11
    mov w11, #0x6c75
    movk w11, #0x7374, lsl #16
    ccmp w10, w11, #0, eq
    b.ne .Lpark
    ldr w9, [x0, #52]               /* NUL and padding */
    cbnz w9, .Lpark
    /* v306: cpu0 reg and timebase-frequency property offsets from metadata. */
    ldr w0, [x24, #N306_META_REG_OFF]
    tst w0, #3
    b.ne .Lpark
    cmp w0, #36
    b.lo .Lpark
    add x9, x0, #4
    cmp x9, x25
    b.hi .Lpark
    add x0, x6, x0
    sub x0, x0, #36
    ldr w9, [x0]                    /* name "reg\0" */
    mov w10, #0x6572
    movk w10, #0x67, lsl #16
    cmp w9, w10
    b.ne .Lpark
    ldr w9, [x0, #32]
    cmp w9, #4
    b.ne .Lpark
    ldr w2, [x0, #36]               /* cpu0 reg */
    ldr w0, [x24, #N306_META_TBF_OFF]
    tst w0, #3
    b.ne .Lpark
    cmp w0, #36
    b.lo .Lpark
    add x9, x0, #4
    cmp x9, x25
    b.hi .Lpark
    add x0, x6, x0
    sub x0, x0, #36
    ldr w9, [x0]                    /* name prefix "time" */
    mov w10, #0x6974
    movk w10, #0x656d, lsl #16
    cmp w9, w10
    b.ne .Lpark
    ldr w9, [x0, #4]                /* name prefix "base" */
    mov w10, #0x6162
    movk w10, #0x6573, lsl #16
    cmp w9, w10
    b.ne .Lpark
    ldr w9, [x0, #32]
    cmp w9, #4
    b.ne .Lpark
    ldr w1, [x0, #36]               /* cpu0 timebase-frequency */
    /* v306: live register cross-checks; MMFR0 is observational. */
    mrs x15, mpidr_el1
    mov x9, #0xffffff
    movk x9, #0xff, lsl #32         /* N306_MPIDR_MASK */
    and x9, x15, x9
    cmp x9, x2
    b.ne .Lpark
    mrs x9, cntfrq_el0
    cmp w9, w1
    b.ne .Lpark
    /* v311: Mach-O header at B + kernel offset, then the word-FNV of the whole image timed by CNTVCT.
     * Scratch x0, x7-x12; x16 = (ticks << 32) | image hash for r[2]. */
    ldr w8, [x24, #N311_META_IMAGE_BYTES]
    mov x7, #(N311_KERNEL_OFFSET & 0xffff)
    movk x7, #(N311_KERNEL_OFFSET >> 16), lsl #16
    add x7, x19, x7
    ldp w9, w10, [x7]               /* magic, cputype */
    mov w11, #(N311_MH_MAGIC & 0xffff)
    movk w11, #(N311_MH_MAGIC >> 16), lsl #16
    mov w12, #(N311_MH_CPU_ARM64 & 0xffff)
    movk w12, #(N311_MH_CPU_ARM64 >> 16), lsl #16
    cmp w9, w11
    ccmp w10, w12, #0, eq
    b.ne .Lpark
    ldr w9, [x7, #12]               /* filetype */
    cmp w9, #N311_MH_EXECUTE
    b.ne .Lpark
    lsr x8, x8, #2
    mov w11, #0x9dc5
    movk w11, #0x811c, lsl #16
    mov w12, #0x193
    movk w12, #0x100, lsl #16
    isb
    mrs x0, cntvct_el0
.Limage:
    ldr w9, [x7], #4
    eor w11, w11, w9
    mul w11, w11, w12
    subs x8, x8, #1
    b.ne .Limage
    isb
    mrs x9, cntvct_el0
    ldr w10, [x24, #N311_META_IMAGE_HASH]
    cmp w11, w10
    b.ne .Lpark
    sub x9, x9, x0
    lsr x10, x9, #32
    cbnz x10, .Lpark
    orr x16, x11, x9, lsl #32
    /* v312: entry_offset (Linux LC_UNIXTHREAD parse) nonzero, 4-aligned, <= image_bytes - 4 (image_bytes checked above);
     * x7 is rematerialized (the hash loop advanced it); x22 = (entry_offset << 32) | entry word for r[3]. Load only. */
    ldr w8, [x24, #N312_META_ENTRY_OFFSET]
    ldr w9, [x24, #N311_META_IMAGE_BYTES]
    cbz w8, .Lpark
    tst w8, #3
    b.ne .Lpark
    sub w9, w9, #4
    cmp w8, w9
    b.hi .Lpark
    mov x7, #(N311_KERNEL_OFFSET & 0xffff)
    movk x7, #(N311_KERNEL_OFFSET >> 16), lsl #16
    add x7, x19, x7
    ldr w9, [x7, x8]
    orr x22, x9, x8, lsl #32
    /* v313 Block A: entry word is an unconditional B; x18 = physical entry (live to the final br); TGran16 is 1 or 2;
     * window end (B + window - 1) < 2^39. Scratch w9-w11 only. */
    and w10, w9, #N313_B_OPCODE_MASK
    movz w11, #(N313_B_OPCODE >> 16), lsl #16
    cmp w10, w11
    b.ne .Lpark
    add x18, x7, x8
    mrs x9, id_aa64mmfr0_el1
    ubfx x9, x9, #N313_MMFR0_TGRAN16_SHIFT, #4
    sub w9, w9, #1
    cmp w9, #1
    b.hi .Lpark
    mov x9, #N311_WINDOW_BYTES
    add x9, x19, x9
    sub x9, x9, #1
    lsr x9, x9, #N313_PA_LIMIT_SHIFT
    cbnz x9, .Lpark
    mov x7, x19
    mov x8, #N304_ARGS_BYTES
    n304_fnv
    ldr w9, [x24, #N304_ARGS_HASH]
    cmp w11, w9
    b.ne .Lpark
    mov w26, w11
    add x7, x19, #N306_ADT_OFFSET
    mov x8, x25
    n304_fnv
    ldr w9, [x24, #N304_ADT_HASH]
    cmp w11, w9
    b.ne .Lpark
    mov w27, w11
    ldp x3, x4, [x24, #N304_RECORD]
    ldr x5, [x24, #N304_NEXT]
    mov x1, #N311_WINDOW_BYTES      /* v311: record/cursor outside the whole window */
    add x1, x19, x1
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
    /* v313 Block B: clean+invalidate every DminLine line of [x3, x3 + record) and the cursor line to PoC before the
     * non-cacheable record/cursor writes, so no stale Linux-era dirty line can overwrite them once XNU enables D-cache.
     * Scratch x0, x9, x10, x12 only. */
    mrs x9, ctr_el0
    ubfx x9, x9, #16, #4
    mov x10, #4
    lsl x10, x10, x9
    sub x12, x10, #1
    bic x9, x3, x12
    add x0, x3, #N315_RECORD_SPAN
.Lclean:
    dc civac, x9
    add x9, x9, x10
    cmp x9, x0
    b.lo .Lclean
    dc civac, x4
    dsb sy
    add x7, x24, #N304_TEXT
    mov x8, #0
.Lcopy:
    ldrb w9, [x7, x8]
    strb w9, [x3, x8]
    add x8, x8, #1
    cmp x8, #N304_RECORD_BYTES
    b.lo .Lcopy
    n304_hex x19, N304_REG_OFFSET, 60
    n304_hex x15, (N304_REG_OFFSET + 17), 60  /* raw MPIDR_EL1 */
    n304_hex x16, (N304_REG_OFFSET + 34), 60  /* v311: (MMU-off image hash ticks << 32) | image word-FNV */
    n304_hex x22, (N304_REG_OFFSET + 51), 60  /* v312: (entry_offset << 32) | entry instruction word */
    n304_hex x26, N304_ARGS_HASH_OFFSET, 28
    n304_hex x27, N304_ADT_HASH_OFFSET, 28
    n304_hex x17, N304_ADT_LENGTH_OFFSET, 4
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
    isb
    mrs x9, cntvct_el0              /* v307: counter advanced since entry */
    cmp x9, x28
    b.ls .Lpark
    mov w9, #'T'
    strb w9, [x3, #N304_COMMIT_OFFSET]
    dsb sy
    str w5, [x4]                    /* 커밋 후 커서 전진 */
    dsb sy
    /* v313: the single XNU branch (CPU0, EL1, MMU/caches off, DAIF masked): x0 = boot_args = B, pc = x18. */
    isb
    mov x0, x19
    br x18
.Lpark:
    yield
    b .Lpark
ENDPROC(n304_post_abi)
.popsection
