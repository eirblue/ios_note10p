/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_dma_pm.h>
static void n10_report_dma_pm(unsigned int generation)
{
    struct n10_dma_pm_sample samples[3] = {0};
    unsigned int sequence, phase;
    int error = n10_dma_pm_read(samples, generation);
    char frame[384];
    for (sequence = 0; sequence < 8; ++sequence) {
        for (phase = 0; phase < 3; ++phase) {
            struct n10_dma_pm_sample *s = &samples[phase];
            int count = scnprintf(frame, sizeof(frame),
                "id=%s seq=%u phase=%u generation=%u seen=%x error=%u total=%x dma=%x suspended=%x direct=%x syscore=%x uncovered=%x prepared=%x active=%x idle=%x other=%x names_xor=%x names_sum=%x status=%u",
                N10_RESERVE_BUILD_ID, sequence * 3 + phase, phase, s->generation, s->seen,
                s->error, s->total, s->dma, s->suspended, s->direct, s->syscore,
                s->uncovered, s->prepared, s->runtime_active, s->runtime_suspended,
                s->runtime_other, s->names_xor, s->names_sum, error ? 1 : 0);
            pr_info("N10DMA1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
        }
    }
}
