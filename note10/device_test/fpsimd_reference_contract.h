/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_FPSIMD_REFERENCE_AUDIT_H
#define NOTE10_FPSIMD_REFERENCE_AUDIT_H
#include <linux/types.h>
struct notifier_block;
struct n10_precond_sample;
struct n10_fps_row { unsigned int index, chain_count, kind, reference, mm, foreign, depth; };
struct n10_fps_sample { unsigned int generation, seen, completed; int error; struct n10_fps_row row; };
int n10_fps_get(struct notifier_block *, struct n10_fps_row *, unsigned int);
void n10_fps_begin(unsigned int);
void n10_fps_invalidate(void);
int n10_fps_collect(struct notifier_block *, unsigned int, unsigned int, unsigned int);
int n10_fps_complete(const struct n10_precond_sample *, unsigned int);
void n10_fps_finish(int);
int n10_fps_copy(struct n10_fps_sample *, unsigned int);
int n10_fps_read(struct n10_fps_sample *, unsigned int);
#endif
