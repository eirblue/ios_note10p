/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_EDGE_DMA_H
#define NOTE10_PM_EDGE_DMA_H
struct n10_edge_dma_sample {
    unsigned int generation, phase, seen, error, total, dma;
    unsigned int prepared, suspended, late, noirq, direct, syscore;
    unsigned int covered, exception_direct, exception_syscore, uncovered;
    unsigned int active, runtime_suspended, runtime_other, names_xor, names_sum;
};
void n10_edge_capture(unsigned int phase, unsigned int generation);
void n10_edge_dma_capture(unsigned int phase, unsigned int generation);
int n10_edge_dma_read(struct n10_edge_dma_sample *out, unsigned int completed);
#endif
