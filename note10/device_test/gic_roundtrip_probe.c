/* SPDX-License-Identifier: GPL-2.0-only */
/* Called only after the successful restored PM/payload checks. */
#include <linux/note10_gic_roundtrip.h>
static void n10_test_gic(void)
{
    struct n10_gic_sample samples[8] = {0};
    unsigned long long before = n10_online_bits(), after;
    unsigned int cpu, sequence;
    char frame[384];
    int error = n10_gic_roundtrip(samples, 8);
    after = n10_online_bits();
    if (!error && (before != 255 || after != before)) error = -EBUSY;
    for (sequence = 0; sequence < 32; ++sequence) {
        for (cpu = 0; cpu < 8; ++cpu) {
            struct n10_gic_sample *s = &samples[cpu];
            int count = scnprintf(frame, sizeof(frame),
                "id=%s seq=%u cpu=%u ctlr=%x pmr=%x masked=%x restored=%x bpr=%x ctlr_after=%x bpr_after=%x dist=%x typer=%x iidr=%x irq_before=%x irq_after=%x seen=%x status=%u",
                N10_RESERVE_BUILD_ID, sequence, cpu, s->ctlr, s->pmr, s->masked,
                s->restored, s->bpr, s->ctlr_after, s->bpr_after, s->dist_ctlr,
                s->typer, s->iidr, s->irq_before, s->irq_after, s->seen, s->status);
            pr_info("N10GIC1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
        }
        {
            int count = scnprintf(frame, sizeof(frame),
                "id=%s seq=%u before=%llx after=%llx cpus=8 error=%u status=%u",
                N10_RESERVE_BUILD_ID, sequence, before, after,
                (unsigned int)(error < 0 ? -error : error), error ? 1 : 0);
            pr_info("N10GIC2 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
        }
    }
}
