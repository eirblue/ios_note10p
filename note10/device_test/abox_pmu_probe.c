/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_abox_pmu.h>
static void n10_report_abox_pmu(unsigned int generation)
{
    static struct n10_abox_pmu_sample samples[3];
    unsigned int copy, phase, core;
    int error = n10_abox_pmu_read(samples, generation);
    char frame[384];
    for (copy = 0; copy < 4; ++copy)
        for (phase = 0; phase < 3; ++phase) {
            struct n10_abox_pmu_sample *s = &samples[phase];
            int count = scnprintf(frame, sizeof(frame),
                "id=%s seq=%u phase=%u generation=%u count=%x seen=%x error=%u before=%x state=%x after=%x status=%u",
                N10_RESERVE_BUILD_ID, copy * 3 + phase, phase, s->generation,
                16, s->seen, s->error, s->domain_before, s->domain_state, s->domain_after, error ? 1 : 0);
            pr_info("N10PDS1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
        }
    for (copy = 0; copy < 4; ++copy)
        for (phase = 0; phase < 3; ++phase)
            for (core = 0; core < 2; ++core) {
                struct n10_abox_pmu_sample *s = &samples[phase];
                int count = scnprintf(frame, sizeof(frame),
                    "id=%s seq=%u phase=%u generation=%u index=%x count=%x seen=%x error=%u power=%x enable=%x standby=%x status=%u",
                    N10_RESERVE_BUILD_ID, (copy * 3 + phase) * 2 + core, phase, s->generation,
                    core, s->count, s->seen, s->error, s->power[core], s->enable[core], s->standby[core], error ? 1 : 0);
                pr_info("N10APM1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
            }
}
