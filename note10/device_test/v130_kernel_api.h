/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N130_KERNEL_API_H
#define N130_KERNEL_API_H
#include <linux/v130_handoff_core.h>
struct kimage;struct device;struct dwc3;struct dma_device;
int n130_before_shutdown(const struct kimage *);
int n130_after_shutdown(void);
int n130_recovery_claim(void);
int n130_dma_record(struct device *,int);
int n130_dma_ready(struct device *);
int n130_usb_prepare(void);
int n130_usb_final(void);
int n130_usb_gadget_quiet(struct dwc3 *);
int n130_ufs_prepare(void);
int n130_dmaengine_prepare(void);
int n130_dmaengine_final(void);
int n130_pl330_preflight(struct dma_device *);
int n130_pl330_quiet(struct dma_device *);
int n130_iommu_prepare(void);
int n130_iommu_final(void);
int n130_gic_platform(struct n130_platform *);
int n130_gic_final(void);
int n130_timer_platform(struct n130_platform *);
int n130_timer_final(void);
#endif
