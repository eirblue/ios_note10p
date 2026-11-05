/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N130_GATE_CORE_H
#define N130_GATE_CORE_H
/* DWC3 source masks are supplied by its actual core.h, not MMIO addresses. */
static inline int n130_usb_halted(unsigned int dctl,unsigned int dsts,unsigned int mode,
    unsigned int event,unsigned int run_mask,unsigned int halt_mask,unsigned int role_mask,
    unsigned int peripheral,unsigned int event_mask,int bound)
{
    return !bound && !(dctl&run_mask) && (dsts&halt_mask) &&
        (mode&role_mask)==peripheral && event==event_mask;
}
#endif
