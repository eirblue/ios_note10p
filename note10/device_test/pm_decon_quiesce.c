/* SPDX-License-Identifier: GPL-2.0-only */
/* Included at the end of decon_core.c for CONFIG_NOTE10_PM_QUIESCE. */
static DEFINE_MUTEX(n10_decon_q_lock);
static struct task_struct *n10_decon_q_owner;
static enum decon_state n10_decon_q_old_state = DECON_STATE_OFF;
static unsigned int n10_decon_q_cookie;
static bool n10_decon_q_active;
static bool n10_decon_q_changed;

bool n10_decon_quiesce_owned(void)
{
    return READ_ONCE(n10_decon_q_active) && READ_ONCE(n10_decon_q_owner) == current;
}

int n10_decon_quiesce_begin(struct n10_pm_result *out)
{
    struct decon_device *decon = get_decon_drvdata(0);
    int ret;
    if (!out || !decon || decon->id || !decon->lcd_info ||
        decon->dt.out_type != DECON_OUT_DSI || !decon->out_sd[0] ||
        !decon->dsim_sd[0] ||
        (decon->state != DECON_STATE_OFF && decon->state != DECON_STATE_INIT &&
         decon->state != DECON_STATE_ON))
        return -EBUSY;
    if (!mutex_trylock(&n10_decon_q_lock))
        return -EBUSY;
    if (n10_decon_q_active) {
        mutex_unlock(&n10_decon_q_lock);
        return -EBUSY;
    }
    n10_decon_q_old_state = decon->state;
    n10_decon_q_owner = current;
    if (!++n10_decon_q_cookie) ++n10_decon_q_cookie;
    out->decon_cookie = n10_decon_q_cookie;
    n10_decon_q_active = true;
    n10_decon_q_changed = false;
    out->qphase = N10_Q_DISPLAY_OFF;
    if (IS_DECON_OFF_STATE(decon)) {
        mutex_unlock(&n10_decon_q_lock);
        return 0;
    }
    ret = decon_update_pwr_state(decon, DISP_PWR_OFF);
    /* The normal OFF path can mutate IRQ/PHY state before updating the enum. */
    n10_decon_q_changed = true;
    if (ret) {
        mutex_unlock(&n10_decon_q_lock);
        return ret;
    }
    if (!IS_DECON_OFF_STATE(decon) || decon->cur_using_dpp ||
        atomic_read(&decon->up.remaining_frame)) {
        mutex_unlock(&n10_decon_q_lock);
        return -EBUSY;
    }
    mutex_unlock(&n10_decon_q_lock);
    return 0;
}

int n10_decon_quiesce_end(struct n10_pm_result *out)
{
    struct decon_device *decon = get_decon_drvdata(0);
    int ret = 0;
    if (!out || !mutex_trylock(&n10_decon_q_lock))
        return -EBUSY;
    if (!out->decon_cookie || out->decon_cookie != n10_decon_q_cookie) {
        mutex_unlock(&n10_decon_q_lock);
        return 0;
    }
    if (!n10_decon_q_active || n10_decon_q_owner != current || !decon) {
        mutex_unlock(&n10_decon_q_lock);
        return -EPERM;
    }
    if (!n10_decon_q_changed) {
        /* Failed before changing hardware, or the display was already OFF. */
        if (decon->state != n10_decon_q_old_state) ret = -EIO;
    } else if (n10_decon_q_old_state == DECON_STATE_OFF) {
        if (!IS_DECON_OFF_STATE(decon)) ret = -EIO;
    } else {
        if (!IS_DECON_OFF_STATE(decon))
            ret = decon_update_pwr_state(decon, DISP_PWR_OFF);
        if (!ret && !IS_DECON_OFF_STATE(decon)) ret = -EBUSY;
        if (!ret) ret = decon_update_pwr_state(decon, DISP_PWR_NORMAL);
        if (!ret && (decon->state != DECON_STATE_ON || !decon->out_sd[0] ||
                     !decon->dsim_sd[0] || !decon->eint_status))
            ret = -EIO;
    }
    if (!ret) {
        n10_decon_q_active = false;
        n10_decon_q_changed = false;
        n10_decon_q_owner = NULL;
    }
    mutex_unlock(&n10_decon_q_lock);
    return ret;
}
