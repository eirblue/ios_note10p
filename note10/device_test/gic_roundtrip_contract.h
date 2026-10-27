/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_GIC_ROUNDTRIP_CONTRACT_H
#define NOTE10_GIC_ROUNDTRIP_CONTRACT_H
struct n10_gic_sample {
    unsigned int ctlr, pmr, masked, restored, bpr, ctlr_after, bpr_after;
    unsigned int dist_ctlr, typer, iidr, irq_before, irq_after, seen, status;
};
int n10_gic_roundtrip(struct n10_gic_sample *samples, unsigned int count);
#endif
