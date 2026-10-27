/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_iommu_pm.h>
static void n10_report_iommu_pm(unsigned int generation)
{
    static struct n10_iommu_pm_sample samples[3];
    unsigned int copy, phase, index, byte;
    int error;
    char frame[512];
    /* One owned PM worker reports; keep the bounded identity inventory off-stack. */
    memset(samples, 0, sizeof(samples));
    error = n10_iommu_pm_read(samples, generation);
    for (copy = 0; copy < 8; ++copy) {
        for (phase = 0; phase < 3; ++phase) {
            struct n10_iommu_pm_sample *s = &samples[phase];
            int count = scnprintf(frame, sizeof(frame),
                "id=%s seq=%u phase=%u generation=%u seen=%x error=%u total=%x active=%x suspended=%x runtime=%x manual_off=%x manual_on=%x boot_hold=%x secure_configured=%x mapped=%x syscore=%x prepared=%x pm_suspended=%x runtime_other=%x names_xor=%x names_sum=%x policy_active=%x exceptions=%x status=%u",
                N10_RESERVE_BUILD_ID, copy * 3 + phase, phase, s->generation,
                s->seen, s->error, s->total, s->active, s->suspended, s->runtime,
                s->manual_off, s->manual_on, s->boot_hold, s->secure_configured, s->mapped, s->syscore, s->prepared, s->pm_suspended,
                s->runtime_other, s->names_xor, s->names_sum, s->policy_active, s->detail_count, error ? 1 : 0);
            pr_info("N10MMU2 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
            if (copy >= 4) continue;
            for (index = 0; index < (s->detail_count ? s->detail_count : 1); ++index) {
                struct n10_iommu_pm_detail empty = {0};
                struct n10_iommu_pm_detail *d = s->detail_count ? &s->details[index] : &empty;
                const char digits[] = "0123456789abcdef";
                char encoded[129] = "00";
                for (byte = 0; byte < d->length; ++byte) {
                    encoded[byte * 2] = digits[((unsigned char)d->name[byte]) >> 4];
                    encoded[byte * 2 + 1] = digits[((unsigned char)d->name[byte]) & 15];
                }
                if (d->length) encoded[d->length * 2] = 0;
                count = scnprintf(frame, sizeof(frame),
                    "id=%s seq=%u phase=%u generation=%u index=%u count=%u length=%u name=%s activations=%x runtime_count=%x manual=%x active=%x suspended=%x effective=%x syscore=%x prepared=%x pm_suspended=%x hold=%x secure=%x mapped=%x status=%u",
                    N10_RESERVE_BUILD_ID, copy * 24 + phase * 8 + index, phase, s->generation,
                    index, s->detail_count, d->length, encoded, d->activations, d->runtime_count,
                    d->manual, d->active, d->suspended, d->effective, d->syscore, d->prepared,
                    d->pm_suspended, d->hold, d->secure, d->mapped, error ? 1 : 0);
                pr_info("N10MMD1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
            }
        }
    }
}
