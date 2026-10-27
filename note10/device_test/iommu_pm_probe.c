/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_iommu_pm.h>
static void n10_report_iommu_pm(unsigned int generation)
{
    struct n10_iommu_pm_sample samples[3] = {0};
    unsigned int copy, phase;
    int error = n10_iommu_pm_read(samples, generation);
    char frame[512];
    for (copy = 0; copy < 8; ++copy) {
        for (phase = 0; phase < 3; ++phase) {
            struct n10_iommu_pm_sample *s = &samples[phase];
            int count = scnprintf(frame, sizeof(frame),
                "id=%s seq=%u phase=%u generation=%u seen=%x error=%u total=%x active=%x suspended=%x runtime=%x manual_off=%x manual_on=%x boot_hold=%x secure_configured=%x mapped=%x syscore=%x prepared=%x pm_suspended=%x runtime_other=%x names_xor=%x names_sum=%x status=%u",
                N10_RESERVE_BUILD_ID, copy * 3 + phase, phase, s->generation,
                s->seen, s->error, s->total, s->active, s->suspended, s->runtime,
                s->manual_off, s->manual_on, s->boot_hold, s->secure_configured, s->mapped, s->syscore, s->prepared, s->pm_suspended,
                s->runtime_other, s->names_xor, s->names_sum, error ? 1 : 0);
            pr_info("N10MMU1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
        }
    }
}
