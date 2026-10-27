/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_abox_pm.h>
static void n10_report_abox_pm(unsigned int generation)
{
    static struct n10_abox_pm_sample samples[3];
    unsigned int copy, phase;
    int error = n10_abox_pm_read(samples, generation);
    char frame[896];
    for (copy = 0; copy < 8; ++copy) {
        for (phase = 0; phase < 3; ++phase) {
            struct n10_abox_pm_sample *s = &samples[phase];
            int count = scnprintf(frame, sizeof(frame),
                "id=%s seq=%u phase=%u generation=%u seen=%x error=%u enabled=%x restored=%x firmware=%x fw_version=%x audio=%x cpu_gear=%x runtime=%x usage=%x usage_negative=%x children=%x depth=%x runtime_error=%x prepared=%x suspended=%x head=%x tail=%x queued=%x interfaces=%x rdma=%x wdma=%x events=%x enables=%x disables=%x ipc_seen=%x ipc_called=%x pending=%x enable_error=%x ipc_error=%x worker_starts=%x worker_finishes=%x worker_stage=%x worker_inflight=%x pm_get_result=%x pm_get_negative=%x gate_seen=%x can_ipc=%x work_pending=%x puts=%x put_busy=%x gets=%x get_empty=%x status=%u",
                N10_RESERVE_BUILD_ID, copy * 3 + phase, phase, s->generation, s->seen, s->error, s->enabled, s->restored, s->firmware, s->fw_version, s->audio, s->cpu_gear, s->runtime, s->usage, s->usage_negative, s->children, s->depth, s->runtime_error, s->prepared, s->suspended, s->head, s->tail, s->queued, s->interfaces, s->rdma, s->wdma, s->events, s->enables, s->disables, s->ipc_seen, s->ipc_called, s->pending, s->enable_error, s->ipc_error, s->worker_starts, s->worker_finishes, s->worker_stage, s->worker_inflight, s->pm_get_result, s->pm_get_negative, s->gate_seen, s->can_ipc, s->work_pending, s->puts, s->put_busy, s->gets, s->get_empty, error ? 1 : 0);
            pr_info("N10ABX3 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
            if (copy < 4) {
                count = scnprintf(frame, sizeof(frame),
                    "id=%s seq=%u phase=%u generation=%u fw_downloads=%x fw_result=%x fw_negative=%x notify_prepares=%x notify_stage=%x clearable_seen=%x clearable=%x suspend_calls=%x suspend_result=%x suspend_negative=%x notify_bad=%x notify_done=%x status=%u",
                    N10_RESERVE_BUILD_ID, copy * 3 + phase, phase, s->generation, s->fw_downloads, s->fw_result, s->fw_negative, s->notify_prepares, s->notify_stage, s->clearable_seen, s->clearable, s->suspend_calls, s->suspend_result, s->suspend_negative, s->notify_bad, s->notify_done, error ? 1 : 0);
                pr_info("N10ABR1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
            }
        }
    }
}
