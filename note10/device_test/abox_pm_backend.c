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
    spin_lock_irqsave(&data->ipc_queue_lock, flags);
    s->head = data->ipc_queue_start; s->tail = data->ipc_queue_end;
    spin_unlock_irqrestore(&data->ipc_queue_lock, flags);
    s->error = 7;
    if (s->head >= ABOX_IPC_QUEUE_SIZE || s->tail >= ABOX_IPC_QUEUE_SIZE ||
        s->firmware > CALLIOPE_ENABLED || s->runtime > RPM_SUSPENDING ||
        s->interfaces > 8 || s->rdma > 16 || s->wdma > 16 || s->children > 4096) goto unlock;
    s->queued = (s->tail + ABOX_IPC_QUEUE_SIZE - s->head) % ABOX_IPC_QUEUE_SIZE;
    spin_lock_irqsave(&n10_abox_event_lock, flags);
    s->error = 8;
    if (n10_abox_history.events && n10_abox_event_device != &pdev->dev) {
        spin_unlock_irqrestore(&n10_abox_event_lock, flags);
        goto unlock;
    }
    s->events = n10_abox_history.events; s->enables = n10_abox_history.enables;
    s->disables = n10_abox_history.disables; s->ipc_seen = n10_abox_history.ipc_seen;
    s->ipc_called = n10_abox_history.ipc_called; s->pending = n10_abox_history.pending;
    s->enable_error = n10_abox_history.enable_error; s->ipc_error = n10_abox_history.ipc_error;
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
        if (out[phase].seen != 1 || out[phase].error || out[phase].phase != phase ||
            out[phase].generation != begin) return -EIO;
    return 0;
}
