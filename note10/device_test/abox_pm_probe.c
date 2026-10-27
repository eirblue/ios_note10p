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
            pr_info("N10ABX8 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
            if (copy < 4) {
                count = scnprintf(frame, sizeof(frame),
                    "id=%s seq=%u phase=%u generation=%u enable_order=%x firmware_order=%x notifier_order=%x qos_begin_order=%x qos_end_order=%x worker_end_order=%x system_get_order=%x system_put_order=%x async_resume_order=%x async_skip_order=%x status=%u",
                    N10_RESERVE_BUILD_ID, copy * 3 + phase, phase, s->generation, s->enable_order, s->firmware_order, s->notifier_order, s->qos_begin_order, s->qos_end_order, s->worker_end_order, s->system_get_order, s->system_put_order, s->async_resume_order, s->async_skip_order, error ? 1 : 0);
                pr_info("N10ABO1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));

                count = scnprintf(frame, sizeof(frame),
                    "id=%s seq=%u phase=%u generation=%u rpm_request=%x rpm_request_pending=%x rpm_deferred_resume=%x rpm_idle_notification=%x rpm_use_autosuspend=%x rpm_timer_autosuspends=%x rpm_timer_armed=%x async_resume_count=%x async_resume_result=%x async_resume_negative=%x async_resume_before=%x async_resume_after=%x async_resume_before_negative=%x async_resume_after_negative=%x async_fw_present=%x async_fw_present_count=%x async_fw_absent_count=%x async_fw_skipped_count=%x async_guard_enabled=%x status=%u",
                    N10_RESERVE_BUILD_ID, copy * 3 + phase, phase, s->generation, s->rpm_request, s->rpm_request_pending, s->rpm_deferred_resume, s->rpm_idle_notification, s->rpm_use_autosuspend, s->rpm_timer_autosuspends, s->rpm_timer_armed, s->async_resume_count, s->async_resume_result, s->async_resume_negative, s->async_resume_before, s->async_resume_after, s->async_resume_before_negative, s->async_resume_after_negative, s->async_fw_present, s->async_fw_present_count, s->async_fw_absent_count, s->async_fw_skipped_count, s->async_guard_enabled, error ? 1 : 0);
                pr_info("N10ABT2 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));

                count = scnprintf(frame, sizeof(frame),
                    "id=%s seq=%u phase=%u generation=%u system_get_count=%x system_get_result=%x system_get_negative=%x system_get_before=%x system_get_after=%x system_get_before_negative=%x system_get_after_negative=%x system_put_count=%x system_put_result=%x system_put_negative=%x system_put_before=%x system_put_after=%x system_put_before_negative=%x system_put_after_negative=%x system_error_put_count=%x system_error_put_result=%x system_error_put_negative=%x system_error_put_before=%x system_error_put_after=%x system_error_put_before_negative=%x system_error_put_after_negative=%x status=%u",
                    N10_RESERVE_BUILD_ID, copy * 3 + phase, phase, s->generation, s->system_get_count, s->system_get_result, s->system_get_negative, s->system_get_before, s->system_get_after, s->system_get_before_negative, s->system_get_after_negative, s->system_put_count, s->system_put_result, s->system_put_negative, s->system_put_before, s->system_put_after, s->system_put_before_negative, s->system_put_after_negative, s->system_error_put_count, s->system_error_put_result, s->system_error_put_negative, s->system_error_put_before, s->system_error_put_after, s->system_error_put_before_negative, s->system_error_put_after_negative, error ? 1 : 0);
                pr_info("N10ABD1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));

                count = scnprintf(frame, sizeof(frame),
                    "id=%s seq=%u phase=%u generation=%u late_state=%x probe_get_count=%x probe_get_result=%x probe_get_negative=%x probe_get_before=%x probe_get_after=%x probe_get_before_negative=%x probe_get_after_negative=%x late_put_count=%x late_put_result=%x late_put_negative=%x late_put_before=%x late_put_after=%x late_put_before_negative=%x late_put_after_negative=%x status=%u",
                    N10_RESERVE_BUILD_ID, copy * 3 + phase, phase, s->generation, s->late_state, s->probe_get_count, s->probe_get_result, s->probe_get_negative, s->probe_get_before, s->probe_get_after, s->probe_get_before_negative, s->probe_get_after_negative, s->late_put_count, s->late_put_result, s->late_put_negative, s->late_put_before, s->late_put_after, s->late_put_before_negative, s->late_put_after_negative, error ? 1 : 0);
                pr_info("N10ABL1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));

                count = scnprintf(frame, sizeof(frame),
                    "id=%s seq=%u phase=%u generation=%u fw_downloads=%x fw_result=%x fw_negative=%x notify_prepares=%x notify_stage=%x clearable_seen=%x clearable=%x suspend_calls=%x suspend_result=%x suspend_negative=%x notify_bad=%x notify_done=%x status=%u",
                    N10_RESERVE_BUILD_ID, copy * 3 + phase, phase, s->generation, s->fw_downloads, s->fw_result, s->fw_negative, s->notify_prepares, s->notify_stage, s->clearable_seen, s->clearable, s->suspend_calls, s->suspend_result, s->suspend_negative, s->notify_bad, s->notify_done, error ? 1 : 0);
                pr_info("N10ABR1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
                count = scnprintf(frame, sizeof(frame),
                    "id=%s seq=%u phase=%u generation=%u qos_seen=%x qos_error=%x qos_registered=%x qos_active=%x qos_target=%x qos_applied=%x qos_absolute=%x qos_default=%x qos_first_id=%x qos_first_value=%x qos_work_pending=%x qos_gets=%x qos_puts=%x qos_get_result=%x qos_get_negative=%x qos_put_result=%x qos_put_negative=%x qos_worker_starts=%x qos_worker_finishes=%x qos_worker_inflight=%x status=%u",
                    N10_RESERVE_BUILD_ID, copy * 3 + phase, phase, s->generation, s->qos_seen, s->qos_error, s->qos_registered, s->qos_active, s->qos_target, s->qos_applied, s->qos_absolute, s->qos_default, s->qos_first_id, s->qos_first_value, s->qos_work_pending, s->qos_gets, s->qos_puts, s->qos_get_result, s->qos_get_negative, s->qos_put_result, s->qos_put_negative, s->qos_worker_starts, s->qos_worker_finishes, s->qos_worker_inflight, error ? 1 : 0);
                pr_info("N10ABQ1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
            }
        }
    }
}
