/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_V136_TERMINAL_H
#define NOTE10_V136_TERMINAL_H
#include <linux/types.h>
#include <linux/errno.h>
struct device;
struct npu_device;
struct n136_detail { const char *reason; unsigned int item; u32 state; int value; u32 aux; };
enum n136_witness_type {
    N136_NO_WITNESS=0,
    N136_SCORE_RESET_DMA_FROZEN=1,
    N136_G2D_FINITE_JOBS_FROZEN=2,
    N136_NPU_DOMAINS_OFF_FROZEN=3,
    N136_SCORE_DOMAINS_OFF_FROZEN=4,
    N136_G2D_DOMAIN_OFF_FROZEN=5
};
struct n136_witness { struct device *owner; unsigned int type, domains; bool committed; };
#define N136_NPU_DOMAINS ((1U<<1)|(1U<<2))
#define N136_SCORE_DOMAINS ((1U<<4)|(1U<<5))
#define N136_G2D_DOMAINS (1U<<6)
#define N136_OPEN (1U<<0)
#define N136_RESUME (1U<<1)
#define N136_DEBUG (1U<<2)
#define N136_REPORT (1U<<3)
#define N136_FAULT (1U<<4)
#define N136_MEMORY (1U<<5)
#define N136_DETACH (1U<<6)
int n136_cal_begin(unsigned int domains,struct n136_detail *detail);
void n136_cal_end(unsigned int domains,bool commit);
bool n136_cal_frozen(unsigned int domains);
int n136_witness_commit(struct n136_witness *witness,struct device *owner,
                       unsigned int type,unsigned int domains);
bool n136_witness_valid(const struct n136_witness *witness,struct device *owner,
                       unsigned int type,unsigned int domains);
int n136_npu_register(struct npu_device *device);
void n136_npu_ready(struct npu_device *device);
void n136_npu_detach(struct npu_device *device);
bool n136_npu_event(unsigned int event);
bool n136_npu_user_begin(void);
void n136_npu_user_end(void);
int n136_npu_protocol_cold(struct npu_device *device,struct n136_detail *detail);
int n136_npu_interface_cold(struct npu_device *device,struct n136_detail *detail);
int n136_npu_prepare(void);
/* Macro-shaped native SRAM/unittest openings also use this exact gate. */
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
#define N136_DEBUG_ADMIT() n136_npu_event(N136_DEBUG)
#else
#define N136_DEBUG_ADMIT() true
#endif
#endif
