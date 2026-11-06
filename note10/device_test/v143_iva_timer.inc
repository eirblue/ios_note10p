/* SPDX-License-Identifier: GPL-2.0-only */
/* Timer-pointer lifetime only; no DMA, file, firmware or MMIO ownership proof. */
#include <linux/errno.h>
#include <linux/mutex.h>
#include <linux/spinlock.h>
#include <linux/timer.h>

static void n143_timer_probe(struct iva_ipcq *ipcq)
{
    mutex_init(&ipcq->to_lifecycle_lock);
    spin_lock_init(&ipcq->to_state_lock);
    ipcq->to_closed = true;
    ipcq->to_removing = false;
    ipcq->to_arm_refused_after_dispatch = false;
}

/* Process lifecycle caller holds to_lifecycle_lock, never a callback lock. */
static void n143_timer_close_locked(struct iva_ipcq *ipcq, bool removing)
{
    unsigned long flags;
    spin_lock_irqsave(&ipcq->to_state_lock, flags);
    ipcq->to_closed = true;
    if (removing)
        ipcq->to_removing = true;
    spin_unlock_irqrestore(&ipcq->to_state_lock, flags);
    /* Callback/IRQ/response paths never acquire to_lifecycle_lock. */
    del_timer_sync(&ipcq->to_timer);
}

static bool n143_timer_removing_locked(struct iva_ipcq *ipcq)
{
    unsigned long flags;
    bool removing;
    spin_lock_irqsave(&ipcq->to_state_lock, flags);
    removing = ipcq->to_removing;
    spin_unlock_irqrestore(&ipcq->to_state_lock, flags);
    return removing;
}

/* Only the successful native init tail calls this, under lifecycle lock. */
static int n143_timer_open_locked(struct iva_ipcq *ipcq)
{
    unsigned long flags;
    int result = 0;
    spin_lock_irqsave(&ipcq->to_state_lock, flags);
    if (ipcq->to_removing)
        result = -ESHUTDOWN;
    else
        ipcq->to_closed = false;
    spin_unlock_irqrestore(&ipcq->to_state_lock, flags);
    return result;
}

/* Native command has already been dispatched; refusal is not cancellation. */
static int n143_timer_arm(struct iva_ipcq *ipcq, unsigned int timeout_ms)
{
    unsigned long flags;
    int result = 0;
    spin_lock_irqsave(&ipcq->to_state_lock, flags);
    if (ipcq->to_closed || ipcq->to_removing) {
        ipcq->to_arm_refused_after_dispatch = true;
        result = -ESHUTDOWN;
    } else {
        ipcq->to_in_ms = timeout_ms;
        /* mod_timer returns pending-state 0/1, never an errno. */
        (void)mod_timer(&ipcq->to_timer,
                       jiffies + msecs_to_jiffies(timeout_ms));
    }
    spin_unlock_irqrestore(&ipcq->to_state_lock, flags);
    return result;
}
