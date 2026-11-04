/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_LEGACY_KEXEC_RETURN_H
#define N10_LEGACY_KEXEC_RETURN_H
#include <linux/kexec.h>
#include <linux/legacy_kexec_core.h>
int n10_kexec_check_image(const struct kimage *);
int n10_kexec_final_return(const struct kimage *);
int n10_sec_stage_kexec_recovery(void);
int n10_wdt_stage_kexec_return(struct n10_wdt_witness *);
#endif
