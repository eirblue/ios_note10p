/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N333_HOST_RECORD_H
#define N333_HOST_RECORD_H

/* Synthetic host record. Tag N333PS2 distinguishes it from N304/N306-N332 records; offsets and r[3] are unchanged.
 * v313: the record is committed immediately before the single branch to the XNU entry.
 * v315: up to three 8-byte XNU checkpoint crumbs may follow the record LF, in any order, each at most once.
 * v316: the reused private XNU image still writes the N315 crumbs; only the record tag changes.
 * v317: the private marker-patched XNU image still writes the N315 crumbs; only the record tag changes.
 * v318: the private memcfg-patched XNU image still writes the N315 crumbs; only the record tag changes.
 * v319: the private slid XNU image (virtBase 0xfffffe0006000000) still writes the N315 crumbs; only the record tag changes.
 * v320: the private physmap-patched slid XNU image still writes the N315 crumbs; only the record tag changes.
 * v321: the private GIC-handoff-marked XNU image still writes the N315 crumbs; only the record tag changes.
 * v322: the private constructor-reordered XNU image still writes the N315 crumbs; only the record tag changes.
 * v323: the private IOKit-start (read_random checkpoint) XNU image still writes the N315 crumbs; only the record tag changes.
 * v324: the private PRNG-stub (crypto_funcs_needed checkpoint) XNU image still writes the N315 crumbs; only the record tag changes.
 * v325: the private crypto-funcs-table (pre_irq_unmask checkpoint) XNU image still writes the N315 crumbs; only the record tag changes.
 * v326: the private IRQ/trust-cache (panic_platform_start checkpoint) XNU image still writes the N315 crumbs; only the record tag changes.
 * v327: the private IRQ-identify (interrupt-ID slot table) XNU image still writes the N315 crumbs; only the record tag changes.
 * v328: the private timer-IRQ (PPI 30 filter to sleh_irq) XNU image still writes the N315 crumbs; only the record tag changes.
 * v329: the private SPI-policy (CPU0 PMU quiesce before the first unmask) XNU image still writes the N315 crumbs; only the record tag changes.
 * v330: the private SPI-general (bulk SPI disable at the distributor before the first unmask) XNU image still writes the N315 crumbs; only the record tag changes.
 * v331: the private platform-start XNU image still writes the N315 crumbs; only the record tag changes.
 * v332: the private platform-start-return XNU image still writes the N315 crumbs; only the record tag changes.
 * v333: the private pthread-stop XNU image still writes the N315 crumbs; only the record tag changes. */
#define N304_HOST_RECORD_BYTES 250
#define N304_HOST_COMMIT_OFFSET 7
#define N304_HOST_PENDING '0'
#define N304_HOST_COMMITTED 'T'
#define N304_HOST_LF_OFFSET 249
#define N315_HOST_CRUMB_BYTES 8
#define N315_HOST_C1 "N315E1-\n"     /* XNU entry hook executed */
#define N315_HOST_C2_PREFIX "N315B2" /* bootstrap builder returned; [6] = hex digit of its x0 & 0xf, [7] = '\n' */
#define N315_HOST_C3 "N315M3-\n"     /* XNU reached the instruction before SCTLR_EL1.M=1 */

/* Each id is exactly 32 lowercase hex digits and matches the expected attempt. */
#define N304_HOST_ID_HEX_DIGITS 32
#define N304_HOST_BUILD_OFFSET 12
#define N304_HOST_BOOT_OFFSET 47
#define N304_HOST_ATTEMPT_OFFSET 82
/* Four 16-hex-digit slots: r[0]=x0 (window base), r[1]=raw MPIDR_EL1,
 * r[2]=(MMU-off image hash CNTVCT ticks << 32) | loaded-image word-FNV (v311), r[3]=(entry_offset << 32) | entry instruction word (v312). The stub parks unless x1 == x2 == 0 before recording. */
#define N304_HOST_REG_OFFSET 117
#define N304_HOST_REG_STRIDE 17
#define N304_HOST_ARGS_HASH_OFFSET 187
#define N304_HOST_ADT_HASH_OFFSET 198
#define N304_HOST_ADT_LENGTH_OFFSET 209 /* Two lowercase hex digits: walked ADT node count. */
/* One hex digit encodes architectural DAIF bits [9:6], ordered D/A/I/F. */
#define N304_HOST_DAIF_OFFSET 214
#define N304_HOST_SCTLR_OFFSET 218 /* 16 lowercase hex digits. */
#define N304_HOST_EL_OFFSET 237 /* CurrentEL[3:2], as one digit 0–3. */

/* FNV-1a 32 covers [9, 238). The hash is eight lowercase hex digits. */
#define N304_HOST_BODY_OFFSET 9
#define N304_HOST_BODY_BYTES 229
#define N304_HOST_CSUM_OFFSET 241
#define N304_HOST_FNV_INIT 0x811c9dc5
#define N304_HOST_FNV_PRIME 0x01000193

/* The formatter owns a separate C string terminator. Only the 250 ASCII bytes
 * through LF are serialized. A reader requires the final T, LF and body hash.
 */
#define N304_HOST_FORMAT \
    "N333PS20 id=%s b=%s c=%s r=0000000000000000,0000000000000000,0000000000000000,0000000000000000" \
    " a=00000000 d=00000000 n=00 q=0 s=0000000000000000 e=0 f=00000000\n"

#endif
