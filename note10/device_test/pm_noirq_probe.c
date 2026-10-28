/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_pm_noirq.h>
static void n10_report_pm_noirq(unsigned int generation)
{
    static struct n10_pm_noirq_sample s;
    static struct n10_pmu_noirq_sample p;
    unsigned int copy, negative, magnitude, original, original_negative;
    int error = n10_pm_noirq_read(&s, &p, generation), count;
    char frame[512];
    negative = s.error < 0;
    magnitude = negative ? (unsigned int)(-(long long)s.error) : (unsigned int)s.error;
    original_negative = s.original_error < 0;
    original = original_negative ? (unsigned int)(-(long long)s.original_error) : (unsigned int)s.original_error;
    for (copy = 0; copy < 4; ++copy) {
        count = scnprintf(frame, sizeof(frame),
            "id=%s seq=%u generation=%u seen=%x bad=%x finished=%x stage=%u state=%x phase=%u late=%x late_ok=%x noirq=%x noirq_ok=%x point=%x blocked=%u ops=%x error=%u negative=%x original=%x original_negative=%x status=%u",
            N10_RESERVE_BUILD_ID, copy, s.generation, s.seen, s.bad, s.finished,
            s.stage, s.state, s.phase, s.late, s.late_ok, s.noirq, s.noirq_ok,
            s.point, s.blocked, s.ops_mask, magnitude, negative, original, original_negative, error ? 1 : 0);
        pr_info("N10PNQ1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
        count = scnprintf(frame, sizeof(frame),
            "id=%s seq=%u generation=%u pre_early=%x post_early=%x pre_noirq=%x post_noirq=%x status=%u",
            N10_RESERVE_BUILD_ID, copy, s.generation, s.pre_early, s.post_early,
            s.pre_noirq, s.post_noirq, error ? 1 : 0);
        pr_info("N10PNR1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
        count = scnprintf(frame, sizeof(frame),
            "id=%s seq=%u generation=%u seen=%x error=%u count=%x before=%x state=%x after=%x status=%u",
            N10_RESERVE_BUILD_ID, copy, p.generation, p.seen, p.error, 16,
            p.before, p.state, p.after, error ? 1 : 0);
        pr_info("N10PND1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    }
}
