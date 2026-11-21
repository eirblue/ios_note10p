/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N313_HOST_RECORD_H
#define N313_HOST_RECORD_H

/* Synthetic host record. Tag N313PS2 distinguishes it from N304/N306-N312 records; offsets and r[3] are unchanged.
 * v313: the record is committed immediately before the single branch to the XNU entry. */
#define N304_HOST_RECORD_BYTES 250
#define N304_HOST_COMMIT_OFFSET 7
#define N304_HOST_PENDING '0'
#define N304_HOST_COMMITTED 'T'
#define N304_HOST_LF_OFFSET 249

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
    "N313PS20 id=%s b=%s c=%s r=0000000000000000,0000000000000000,0000000000000000,0000000000000000" \
    " a=00000000 d=00000000 n=00 q=0 s=0000000000000000 e=0 f=00000000\n"

#endif
