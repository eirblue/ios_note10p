/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_DMA_PM_CONTRACT_H
#define NOTE10_DMA_PM_CONTRACT_H
/* Framework observations only. Never a DMA-idle or handoff permission. */
struct n10_dma_pm_sample {
    unsigned int generation, phase, seen, error;
    unsigned int total, dma, suspended, direct, syscore, uncovered;
    unsigned int prepared, runtime_active, runtime_suspended, runtime_other;
    unsigned int names_xor, names_sum;
};
void n10_dma_pm_capture(unsigned int phase, unsigned int generation);
int n10_dma_pm_read(struct n10_dma_pm_sample *out, unsigned int generation);
#endif
