/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in pinned ufs-exynos.c. No device/host state or MMIO writes. */
#include <linux/of_platform.h>
#include <linux/note10_ufs_pm.h>
static struct n10_ufs_pm_sample n10_ufs_samples[3];

void n10_ufs_pm_capture(unsigned int phase, unsigned int generation)
{
    struct n10_ufs_pm_sample *s;
    struct device_node *node;
    struct platform_device *pdev;
    struct ufs_hba *hba = NULL;
    unsigned long flags;
    if (phase >= 3) return;
    if (phase == 2) n10_ufs_hci_arm(NULL, 0);
    if (!phase && (!n10_ufs_samples[0].seen || n10_ufs_samples[0].generation != generation))
        memset(n10_ufs_samples, 0, sizeof(n10_ufs_samples));
    s = &n10_ufs_samples[phase];
    if (s->seen++) { s->error = 1; goto finish; }
    s->phase = phase;
    s->generation = generation;
    if (!generation || (phase && (n10_ufs_samples[phase - 1].seen != 1 ||
        n10_ufs_samples[phase - 1].generation != generation))) { s->error = 2; goto finish; }
    node = of_find_compatible_node(NULL, NULL, "samsung,exynos-ufs");
    if (!node) { s->error = 3; goto finish; }
    pdev = of_find_device_by_node(node);
    of_node_put(node);
    if (!pdev) { s->error = 4; goto finish; }
    s->error = 5;
    if (!device_trylock(&pdev->dev)) goto put;
    s->error = 6;
    if (pdev->dev.driver != &exynos_ufs_driver.driver) goto unlock;
    hba = dev_get_drvdata(&pdev->dev);
    if (!hba || hba->dev != &pdev->dev || !hba->host || !hba->host->host_lock) goto unlock;
    spin_lock_irqsave(hba->host->host_lock, flags);
    s->requests = hba->outstanding_reqs;
    s->tasks = hba->outstanding_tasks;
    s->lrb = hba->lrb_in_use;
    s->powered = hba->is_powered;
    s->irq = hba->is_irq_enabled;
    s->system = hba->is_sys_suspended;
    s->busy = hba->pm_op_in_progress;
    s->power = hba->curr_dev_pwr_mode;
    s->link = hba->uic_link_state;
    s->clock = hba->clk_gating.state;
    s->gating = hba->clk_gating.is_suspended;
    s->runtime = READ_ONCE(pdev->dev.power.runtime_status);
    spin_unlock_irqrestore(hba->host->host_lock, flags);
    if (!phase) n10_ufs_hci_arm(hba, generation);
    s->error = 0;
unlock:
    device_unlock(&pdev->dev);
put:
    put_device(&pdev->dev);
finish:
    if (phase == 1) n10_ufs_hci_finish(hba, generation, s);
}

int n10_ufs_pm_read(struct n10_ufs_pm_sample *out, unsigned int completed)
{
    unsigned int phase, begin, next;
    if (!out || !completed) return -EINVAL;
    memcpy(out, n10_ufs_samples, sizeof(n10_ufs_samples));
    begin = out[0].generation;
    next = begin + 1;
    if (!next) next = 1;
    if (!begin || next != completed) return -EIO;
    for (phase = 0; phase < 3; ++phase)
        if (out[phase].seen != 1 || out[phase].error || out[phase].phase != phase ||
            out[phase].generation != begin) return -EIO;
    return 0;
}
