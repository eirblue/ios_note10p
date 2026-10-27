/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_ABOX_PM_CONTRACT_H
#define NOTE10_ABOX_PM_CONTRACT_H
struct device;
struct n10_abox_pm_sample {
    unsigned int phase, generation, seen, error;
    unsigned int enabled, restored, firmware, fw_version, audio, cpu_gear, runtime, usage, usage_negative;
    unsigned int children, depth, runtime_error, prepared, suspended;
    unsigned int head, tail, queued, interfaces, rdma, wdma;
    unsigned int events, enables, disables, ipc_seen, ipc_called, pending;
    unsigned int enable_error, ipc_error;
    unsigned int worker_starts, worker_finishes, worker_stage, worker_inflight;
    unsigned int pm_get_result, pm_get_negative, gate_seen, can_ipc, work_pending;
    unsigned int puts, put_busy, gets, get_empty;
    unsigned int fw_downloads, fw_result, fw_negative;
    unsigned int notify_prepares, notify_stage, clearable_seen, clearable;
    unsigned int suspend_calls, suspend_result, suspend_negative, notify_bad, notify_done;
    unsigned int qos_seen, qos_error, qos_registered, qos_active, qos_target, qos_applied;
    unsigned int qos_absolute, qos_default, qos_first_id, qos_first_value, qos_work_pending;
    unsigned int qos_gets, qos_puts, qos_get_result, qos_get_negative, qos_put_result, qos_put_negative;
    unsigned int qos_worker_starts, qos_worker_finishes, qos_worker_inflight;
};
void n10_abox_note(struct device *dev, unsigned int kind, int error);
void n10_abox_pm_capture(unsigned int phase, unsigned int generation);
void n10_abox_qos_capture(struct device *dev, struct n10_abox_pm_sample *out);
int n10_abox_pm_read(struct n10_abox_pm_sample *out, unsigned int completed);
#endif
