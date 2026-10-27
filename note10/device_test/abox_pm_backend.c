/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in pinned abox.c: no MMIO, PM request or driver-state writes. */
#include <linux/of_platform.h>
#include <linux/note10_abox_pm.h>
static struct n10_abox_pm_sample n10_abox_samples[3], n10_abox_history;
static struct device *n10_abox_event_device;
static DEFINE_SPINLOCK(n10_abox_event_lock);

static unsigned int n10_abox_magnitude(int value)
{
    return value < 0 ? (unsigned int)(-(long long)value) : (unsigned int)value;
}


void n10_abox_async_firmware(struct device *dev, unsigned int present)
{
    unsigned long flags;
    if (dev->driver != &samsung_abox_driver.driver) return;
    spin_lock_irqsave(&n10_abox_event_lock, flags);
    if (n10_abox_event_device != dev) {
        memset(&n10_abox_history, 0, sizeof(n10_abox_history));
        n10_abox_event_device = dev;
    }
    n10_abox_history.async_fw_present = !!present;
    spin_unlock_irqrestore(&n10_abox_event_lock, flags);
}

/* Late init can precede deferred probe: keep this state outside device history. */
static unsigned int n10_abox_late_observed;
void n10_abox_late_state(unsigned int state)
{
    unsigned long flags;
    spin_lock_irqsave(&n10_abox_event_lock, flags);
    n10_abox_late_observed = state;
    spin_unlock_irqrestore(&n10_abox_event_lock, flags);
}
void n10_abox_lifecycle(struct device *dev, unsigned int kind, int result, int before, int after)
{
    unsigned long flags;
    struct n10_abox_pm_sample *h = &n10_abox_history;
    if (kind >= 2 && dev->driver != &samsung_abox_driver.driver) return;
    spin_lock_irqsave(&n10_abox_event_lock, flags);
    if (n10_abox_event_device != dev) {
        memset(h, 0, sizeof(*h));
        n10_abox_event_device = dev;
    }
    if (!++h->events) ++h->events;
    if (kind == 0) {
        ++h->probe_get_count; h->probe_get_result = n10_abox_magnitude(result); h->probe_get_negative = result < 0;
        h->probe_get_before = n10_abox_magnitude(before); h->probe_get_before_negative = before < 0;
        h->probe_get_after = n10_abox_magnitude(after); h->probe_get_after_negative = after < 0;
    }
    else if (kind == 1) {
        ++h->late_put_count; h->late_put_result = n10_abox_magnitude(result); h->late_put_negative = result < 0;
        h->late_put_before = n10_abox_magnitude(before); h->late_put_before_negative = before < 0;
        h->late_put_after = n10_abox_magnitude(after); h->late_put_after_negative = after < 0;
    }
    else if (kind == 2) {
        ++h->system_get_count; h->system_get_result = n10_abox_magnitude(result); h->system_get_negative = result < 0;
        h->system_get_before = n10_abox_magnitude(before); h->system_get_before_negative = before < 0;
        h->system_get_after = n10_abox_magnitude(after); h->system_get_after_negative = after < 0;
    }
    else if (kind == 3) {
        ++h->system_put_count; h->system_put_result = n10_abox_magnitude(result); h->system_put_negative = result < 0;
        h->system_put_before = n10_abox_magnitude(before); h->system_put_before_negative = before < 0;
        h->system_put_after = n10_abox_magnitude(after); h->system_put_after_negative = after < 0;
    }
    else if (kind == 4) {
        ++h->system_error_put_count; h->system_error_put_result = n10_abox_magnitude(result); h->system_error_put_negative = result < 0;
        h->system_error_put_before = n10_abox_magnitude(before); h->system_error_put_before_negative = before < 0;
        h->system_error_put_after = n10_abox_magnitude(after); h->system_error_put_after_negative = after < 0;
    }
    else if (kind == 5) {
        ++h->async_resume_count; h->async_resume_result = n10_abox_magnitude(result); h->async_resume_negative = result < 0;
        h->async_resume_before = n10_abox_magnitude(before); h->async_resume_before_negative = before < 0;
        h->async_resume_after = n10_abox_magnitude(after); h->async_resume_after_negative = after < 0;
        h->async_resume_order = h->events;
    }
    if (kind == 2) h->system_get_order = h->events;
    if (kind == 3) h->system_put_order = h->events;
    spin_unlock_irqrestore(&n10_abox_event_lock, flags);
}

void n10_abox_note(struct device *dev, unsigned int kind, int error)
{
    unsigned long flags;
    struct n10_abox_pm_sample *h = &n10_abox_history;
    spin_lock_irqsave(&n10_abox_event_lock, flags);
    if (n10_abox_event_device != dev) {
        memset(h, 0, sizeof(*h));
        n10_abox_event_device = dev;
    }
    if (!++h->events) ++h->events;
    if (kind == 1) { ++h->enables; h->enable_error = n10_abox_magnitude(error); }
    else if (kind == 2) { h->pending = 1; h->ipc_called = 0; h->ipc_error = 0; }
    else if (kind == 3) { ++h->ipc_seen; h->ipc_called = 1; h->ipc_error = n10_abox_magnitude(error); }
    else if (kind == 4) { ++h->disables; h->pending = 0; }
    else if (kind == 5) { ++h->worker_starts; h->worker_stage = 1; h->worker_inflight = 1; h->gate_seen = 0; h->can_ipc = 0; h->pm_get_result = 0; h->pm_get_negative = 0; }
    else if (kind == 6) { h->worker_stage = 2; h->pm_get_result = n10_abox_magnitude(error); h->pm_get_negative = error < 0; }
    else if (kind == 7) { h->worker_stage = 3; h->gate_seen = 1; h->can_ipc = !!error; }
    else if (kind == 8) { ++h->worker_finishes; h->worker_stage = 4; h->worker_inflight = 0; }
    else if (kind == 9) { if (!error) ++h->puts; else if (error == -EBUSY) ++h->put_busy; }
    else if (kind == 10) { if (!error) ++h->gets; else if (error == -ENODATA) ++h->get_empty; }
    else if (kind == 11) { ++h->fw_downloads; h->fw_result = n10_abox_magnitude(error); h->fw_negative = error < 0; }
    else if (kind == 12) { ++h->notify_prepares; h->notify_stage = 1; h->clearable_seen = 0; h->clearable = 0; h->suspend_result = 0; h->suspend_negative = 0; }
    else if (kind == 13) { h->notify_stage = 2; }
    else if (kind == 14) { h->notify_stage = 3; h->clearable_seen = 1; h->clearable = !!error; }
    else if (kind == 15) { ++h->suspend_calls; h->notify_stage = 4; h->suspend_result = n10_abox_magnitude(error); h->suspend_negative = error < 0; }
    else if (kind == 16) { ++h->notify_bad; h->notify_stage = 5; }
    else if (kind == 17) { ++h->notify_done; h->notify_stage = 6; }
    else if (kind == 18) { ++h->qos_gets; h->qos_get_result = n10_abox_magnitude(error); h->qos_get_negative = error < 0; }
    else if (kind == 19) { ++h->qos_puts; h->qos_put_result = n10_abox_magnitude(error); h->qos_put_negative = error < 0; }
    else if (kind == 20) { ++h->qos_worker_starts; h->qos_worker_inflight = 1; }
    else if (kind == 21) { ++h->qos_worker_finishes; h->qos_worker_inflight = 0; }
    if (kind == 1) h->enable_order = h->events;
    if (kind == 11) h->firmware_order = h->events;
    if (kind == 12) h->notifier_order = h->events;
    if (kind == 20) h->qos_begin_order = h->events;
    if (kind == 21) h->qos_end_order = h->events;
    if (kind == 8) h->worker_end_order = h->events;
    spin_unlock_irqrestore(&n10_abox_event_lock, flags);
}

void n10_abox_pm_capture(unsigned int phase, unsigned int generation)
{
    struct n10_abox_pm_sample *s;
    struct device_node *node;
    struct platform_device *pdev;
    struct abox_data *data;
    unsigned long flags;
    int usage;
    if (phase >= 3) return;
    if (!phase && (!n10_abox_samples[0].seen || n10_abox_samples[0].generation != generation))
        memset(n10_abox_samples, 0, sizeof(n10_abox_samples));
    s = &n10_abox_samples[phase];
    if (s->seen++) { s->error = 1; return; }
    s->phase = phase; s->generation = generation;
    if (!generation || (phase && (n10_abox_samples[phase - 1].seen != 1 ||
        n10_abox_samples[phase - 1].generation != generation))) { s->error = 2; return; }
    node = of_find_compatible_node(NULL, NULL, "samsung,abox");
    if (!node) { s->error = 3; return; }
    pdev = of_find_device_by_node(node); of_node_put(node);
    if (!pdev) { s->error = 4; return; }
    s->error = 5;
    if (!device_trylock(&pdev->dev)) goto put;
    s->error = 6;
    if (pdev->dev.driver != &samsung_abox_driver.driver) goto unlock;
    data = dev_get_drvdata(&pdev->dev);
    if (!data || data->pdev != pdev) goto unlock;
    s->enabled = !!READ_ONCE(data->enabled);
    s->restored = !!READ_ONCE(data->restored);
    s->firmware = READ_ONCE(data->calliope_state);
    s->fw_version = READ_ONCE(data->calliope_version);
    s->cpu_gear = READ_ONCE(data->cpu_gear);
    s->audio = READ_ONCE(data->audio_mode);
    s->runtime = READ_ONCE(pdev->dev.power.runtime_status);
    usage = atomic_read(&pdev->dev.power.usage_count);
    s->usage = n10_abox_magnitude(usage); s->usage_negative = usage < 0;
    s->children = atomic_read(&pdev->dev.power.child_count);
    s->depth = pdev->dev.power.disable_depth;
    s->runtime_error = n10_abox_magnitude(READ_ONCE(pdev->dev.power.runtime_error));
    s->prepared = !!pdev->dev.power.is_prepared;
    s->suspended = !!pdev->dev.power.is_suspended;
    s->interfaces = READ_ONCE(data->if_count);
    s->rdma = READ_ONCE(data->rdma_count); s->wdma = READ_ONCE(data->wdma_count);
    s->work_pending = !!work_pending(&data->ipc_work);
    spin_lock_irqsave(&data->ipc_queue_lock, flags);
    s->head = data->ipc_queue_start; s->tail = data->ipc_queue_end;
    spin_unlock_irqrestore(&data->ipc_queue_lock, flags);
    s->error = 7;
    if (s->head >= ABOX_IPC_QUEUE_SIZE || s->tail >= ABOX_IPC_QUEUE_SIZE ||
        s->firmware > CALLIOPE_ENABLED || s->runtime > RPM_SUSPENDING ||
        s->interfaces > 8 || s->rdma > 16 || s->wdma > 16 || s->children > 4096) goto unlock;
    s->queued = (s->tail + ABOX_IPC_QUEUE_SIZE - s->head) % ABOX_IPC_QUEUE_SIZE;
    spin_lock_irqsave(&pdev->dev.power.lock, flags);
    s->rpm_request = pdev->dev.power.request;
    s->rpm_request_pending = pdev->dev.power.request_pending;
    s->rpm_deferred_resume = pdev->dev.power.deferred_resume;
    s->rpm_idle_notification = pdev->dev.power.idle_notification;
    s->rpm_use_autosuspend = pdev->dev.power.use_autosuspend;
    s->rpm_timer_autosuspends = pdev->dev.power.timer_autosuspends;
    s->rpm_timer_armed = !!pdev->dev.power.timer_expires;
    spin_unlock_irqrestore(&pdev->dev.power.lock, flags);
    n10_abox_qos_capture(&pdev->dev, s);
    s->error = 9;
    if (s->qos_error) goto unlock;
    spin_lock_irqsave(&n10_abox_event_lock, flags);
    s->error = 8;
    if (n10_abox_history.events && n10_abox_event_device != &pdev->dev) {
        spin_unlock_irqrestore(&n10_abox_event_lock, flags);
        goto unlock;
    }
    s->system_get_count = n10_abox_history.system_get_count;
    s->system_get_result = n10_abox_history.system_get_result;
    s->system_get_negative = n10_abox_history.system_get_negative;
    s->system_get_before = n10_abox_history.system_get_before;
    s->system_get_after = n10_abox_history.system_get_after;
    s->system_get_before_negative = n10_abox_history.system_get_before_negative;
    s->system_get_after_negative = n10_abox_history.system_get_after_negative;
    s->system_put_count = n10_abox_history.system_put_count;
    s->system_put_result = n10_abox_history.system_put_result;
    s->system_put_negative = n10_abox_history.system_put_negative;
    s->system_put_before = n10_abox_history.system_put_before;
    s->system_put_after = n10_abox_history.system_put_after;
    s->system_put_before_negative = n10_abox_history.system_put_before_negative;
    s->system_put_after_negative = n10_abox_history.system_put_after_negative;
    s->system_error_put_count = n10_abox_history.system_error_put_count;
    s->system_error_put_result = n10_abox_history.system_error_put_result;
    s->system_error_put_negative = n10_abox_history.system_error_put_negative;
    s->system_error_put_before = n10_abox_history.system_error_put_before;
    s->system_error_put_after = n10_abox_history.system_error_put_after;
    s->system_error_put_before_negative = n10_abox_history.system_error_put_before_negative;
    s->system_error_put_after_negative = n10_abox_history.system_error_put_after_negative;
    s->async_resume_count = n10_abox_history.async_resume_count;
    s->async_resume_result = n10_abox_history.async_resume_result;
    s->async_resume_negative = n10_abox_history.async_resume_negative;
    s->async_resume_before = n10_abox_history.async_resume_before;
    s->async_resume_after = n10_abox_history.async_resume_after;
    s->async_resume_before_negative = n10_abox_history.async_resume_before_negative;
    s->async_resume_after_negative = n10_abox_history.async_resume_after_negative;
    s->async_fw_present = n10_abox_history.async_fw_present;
    s->enable_order = n10_abox_history.enable_order;
    s->firmware_order = n10_abox_history.firmware_order;
    s->notifier_order = n10_abox_history.notifier_order;
    s->qos_begin_order = n10_abox_history.qos_begin_order;
    s->qos_end_order = n10_abox_history.qos_end_order;
    s->worker_end_order = n10_abox_history.worker_end_order;
    s->system_get_order = n10_abox_history.system_get_order;
    s->system_put_order = n10_abox_history.system_put_order;
    s->async_resume_order = n10_abox_history.async_resume_order;
    s->late_state = n10_abox_late_observed;
    s->probe_get_count = n10_abox_history.probe_get_count;
    s->probe_get_result = n10_abox_history.probe_get_result;
    s->probe_get_negative = n10_abox_history.probe_get_negative;
    s->probe_get_before = n10_abox_history.probe_get_before;
    s->probe_get_after = n10_abox_history.probe_get_after;
    s->probe_get_before_negative = n10_abox_history.probe_get_before_negative;
    s->probe_get_after_negative = n10_abox_history.probe_get_after_negative;
    s->late_put_count = n10_abox_history.late_put_count;
    s->late_put_result = n10_abox_history.late_put_result;
    s->late_put_negative = n10_abox_history.late_put_negative;
    s->late_put_before = n10_abox_history.late_put_before;
    s->late_put_after = n10_abox_history.late_put_after;
    s->late_put_before_negative = n10_abox_history.late_put_before_negative;
    s->late_put_after_negative = n10_abox_history.late_put_after_negative;
    s->events = n10_abox_history.events; s->enables = n10_abox_history.enables;
    s->disables = n10_abox_history.disables; s->ipc_seen = n10_abox_history.ipc_seen;
    s->ipc_called = n10_abox_history.ipc_called; s->pending = n10_abox_history.pending;
    s->enable_error = n10_abox_history.enable_error; s->ipc_error = n10_abox_history.ipc_error;
    s->worker_starts = n10_abox_history.worker_starts; s->worker_finishes = n10_abox_history.worker_finishes;
    s->worker_stage = n10_abox_history.worker_stage; s->worker_inflight = n10_abox_history.worker_inflight;
    s->pm_get_result = n10_abox_history.pm_get_result; s->pm_get_negative = n10_abox_history.pm_get_negative;
    s->gate_seen = n10_abox_history.gate_seen; s->can_ipc = n10_abox_history.can_ipc;
    s->puts = n10_abox_history.puts; s->put_busy = n10_abox_history.put_busy;
    s->gets = n10_abox_history.gets; s->get_empty = n10_abox_history.get_empty;
    s->fw_downloads = n10_abox_history.fw_downloads; s->fw_result = n10_abox_history.fw_result;
    s->fw_negative = n10_abox_history.fw_negative;
    s->notify_prepares = n10_abox_history.notify_prepares; s->notify_stage = n10_abox_history.notify_stage;
    s->clearable_seen = n10_abox_history.clearable_seen; s->clearable = n10_abox_history.clearable;
    s->suspend_calls = n10_abox_history.suspend_calls; s->suspend_result = n10_abox_history.suspend_result;
    s->suspend_negative = n10_abox_history.suspend_negative;
    s->notify_bad = n10_abox_history.notify_bad; s->notify_done = n10_abox_history.notify_done;
    s->qos_gets = n10_abox_history.qos_gets; s->qos_puts = n10_abox_history.qos_puts;
    s->qos_get_result = n10_abox_history.qos_get_result; s->qos_get_negative = n10_abox_history.qos_get_negative;
    s->qos_put_result = n10_abox_history.qos_put_result; s->qos_put_negative = n10_abox_history.qos_put_negative;
    s->qos_worker_starts = n10_abox_history.qos_worker_starts;
    s->qos_worker_finishes = n10_abox_history.qos_worker_finishes;
    s->qos_worker_inflight = n10_abox_history.qos_worker_inflight;
    spin_unlock_irqrestore(&n10_abox_event_lock, flags);
    s->error = 0;
unlock:
    device_unlock(&pdev->dev);
put:
    put_device(&pdev->dev);
}

int n10_abox_pm_read(struct n10_abox_pm_sample *out, unsigned int completed)
{
    unsigned int phase, begin, next;
    if (!out || !completed) return -EINVAL;
    memcpy(out, n10_abox_samples, sizeof(n10_abox_samples));
    begin = out[0].generation; next = begin + 1;
    if (!next) next = 1;
    if (!begin || next != completed) return -EIO;
    for (phase = 0; phase < 3; ++phase)
        if (out[phase].seen != 1 || out[phase].error || out[phase].qos_seen != 1 || out[phase].qos_error || out[phase].phase != phase ||
            out[phase].generation != begin) return -EIO;
    return 0;
}
