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
};
void n10_abox_note(struct device *dev, unsigned int kind, int error);
void n10_abox_pm_capture(unsigned int phase, unsigned int generation);
int n10_abox_pm_read(struct n10_abox_pm_sample *out, unsigned int completed);
#endif
