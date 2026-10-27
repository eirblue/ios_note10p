/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in pinned ufshcd.c. Only its held-clock suspend callback reads MMIO. */
#include <linux/note10_ufs_pm.h>
static DEFINE_SPINLOCK(n10_ufs_hci_lock);
static struct ufs_hba *n10_ufs_hci_owner;
static unsigned int n10_ufs_hci_generation;
static struct n10_ufs_pm_sample n10_ufs_hci_sample;

void n10_ufs_hci_arm(struct ufs_hba *hba, unsigned int generation)
{
    unsigned long flags;
    spin_lock_irqsave(&n10_ufs_hci_lock, flags);
    memset(&n10_ufs_hci_sample, 0, sizeof(n10_ufs_hci_sample));
    n10_ufs_hci_owner = hba;
    n10_ufs_hci_generation = generation;
    spin_unlock_irqrestore(&n10_ufs_hci_lock, flags);
}

void n10_ufs_hci_before_clock_off(struct ufs_hba *hba, unsigned int pm_op)
{
    unsigned long flags, capture_flags;
    struct n10_ufs_pm_sample *s = &n10_ufs_hci_sample;
    if (!ufshcd_is_system_pm(pm_op)) return;
    spin_lock_irqsave(hba->host->host_lock, flags);
    spin_lock_irqsave(&n10_ufs_hci_lock, capture_flags);
    if (n10_ufs_hci_owner != hba || !n10_ufs_hci_generation) goto out;
    if (s->hci_seen++) { s->hci_error = 1; goto out; }
    s->hci_error = 2;
    /* The original caller holds clocks, suspends gating and has disabled IRQs.
     * Refuse an unproven state rather than issuing PM requests or enabling clocks.
     */
    if (!hba->mmio_base || !hba->is_powered || hba->is_irq_enabled ||
        !hba->pm_op_in_progress || !hba->clk_gating.is_suspended ||
        hba->clk_gating.state != CLKS_ON ||
        hba->curr_dev_pwr_mode != UFS_POWERDOWN_PWR_MODE ||
        hba->uic_link_state != UIC_LINK_OFF_STATE ||
        hba->outstanding_reqs || hba->outstanding_tasks || hba->lrb_in_use) goto out;
    s->hce = ufshcd_readl(hba, REG_CONTROLLER_ENABLE);
    s->transfer_db = ufshcd_readl(hba, REG_UTP_TRANSFER_REQ_DOOR_BELL);
    s->task_db = ufshcd_readl(hba, REG_UTP_TASK_REQ_DOOR_BELL);
    s->hci_error = 0;
out:
    spin_unlock_irqrestore(&n10_ufs_hci_lock, capture_flags);
    spin_unlock_irqrestore(hba->host->host_lock, flags);
}

void n10_ufs_hci_finish(struct ufs_hba *hba, unsigned int generation,
                       struct n10_ufs_pm_sample *out)
{
    unsigned long flags;
    spin_lock_irqsave(&n10_ufs_hci_lock, flags);
    if (n10_ufs_hci_owner == hba && n10_ufs_hci_generation == generation) {
        out->hci_seen = n10_ufs_hci_sample.hci_seen;
        out->hci_error = n10_ufs_hci_sample.hci_error;
        out->hce = n10_ufs_hci_sample.hce;
        out->transfer_db = n10_ufs_hci_sample.transfer_db;
        out->task_db = n10_ufs_hci_sample.task_db;
    } else out->hci_error = 3;
    n10_ufs_hci_owner = NULL;
    n10_ufs_hci_generation = 0;
    spin_unlock_irqrestore(&n10_ufs_hci_lock, flags);
}
