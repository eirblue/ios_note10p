/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_CURRENT_OWNED_CAPACITY_H
#define N10_CURRENT_OWNED_CAPACITY_H
/* Exact measured source-built v94 software payload span; no RAM authority. */
#define N10_OWNED_BYTES 19136512u
_Static_assert(N10_OWNED_BYTES % 16384u == 0, "whole 16KiB owned pages");
_Static_assert(N10_OWNED_BYTES <= 64u * 1024u * 1024u, "bounded DATA output");
#endif
