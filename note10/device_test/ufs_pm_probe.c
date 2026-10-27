/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_ufs_pm.h>
static void n10_report_ufs_pm(unsigned int generation)
{
    struct n10_ufs_pm_sample samples[3] = {0};
    unsigned int sequence, phase;
    int error = n10_ufs_pm_read(samples, generation);
    char frame[512];
    for (sequence = 0; sequence < 8; ++sequence) {
        for (phase = 0; phase < 3; ++phase) {
            struct n10_ufs_pm_sample *s = &samples[phase];
            int count = scnprintf(frame, sizeof(frame),
                "id=%s seq=%u phase=%u generation=%u seen=%x error=%u requests=%llx tasks=%llx lrb=%llx powered=%x irq=%x system=%x busy=%x power=%x link=%x clock=%x gating=%x runtime=%x hci_seen=%x hci_error=%x hce=%x transfer_db=%x task_db=%x status=%u",
                N10_RESERVE_BUILD_ID, sequence * 3 + phase, phase, s->generation,
                s->seen, s->error, s->requests, s->tasks, s->lrb, s->powered,
                s->irq, s->system, s->busy, s->power, s->link, s->clock,
                s->gating, s->runtime, s->hci_seen, s->hci_error, s->hce, s->transfer_db, s->task_db, error ? 1 : 0);
            pr_info("N10UFS2 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
        }
    }
}
