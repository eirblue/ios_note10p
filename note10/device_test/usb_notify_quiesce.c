/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in pinned usb_notify.c; persistent barriers survive timeout. */
static DEFINE_MUTEX(n10_usb_q_lock);
static struct task_struct *n10_usb_q_owner;
static struct usb_notify *n10_usb_q_notify;
static atomic_t n10_usb_q_epoch = ATOMIC_INIT(0);
static atomic_t n10_usb_q_begin_done = ATOMIC_INIT(0);
static atomic_t n10_usb_q_end_done = ATOMIC_INIT(0);
static unsigned int n10_usb_q_generation, n10_usb_q_expected_epoch;
static int n10_usb_q_original_disable;
static bool n10_usb_q_off;
static int n10_usb_q_transition_error, n10_usb_q_restore_error;
extern int n10_exynos_usb_quiesce_check(bool off);

static void n10_usb_q_begin_barrier(struct work_struct *work)
{
    atomic_set(&n10_usb_q_begin_done, 1);
}
static void n10_usb_q_end_barrier(struct work_struct *work)
{
    atomic_set(&n10_usb_q_end_done, 1);
}
static DECLARE_WORK(n10_usb_q_begin_work, n10_usb_q_begin_barrier);
static DECLARE_WORK(n10_usb_q_end_work, n10_usb_q_end_barrier);

static bool n10_usb_q_wake_active(struct wakeup_source *ws)
{
    unsigned long flags;
    bool active;
    spin_lock_irqsave(&ws->lock, flags);
    active = ws->active;
    spin_unlock_irqrestore(&ws->lock, flags);
    return active;
}

static int n10_usb_policy_enter(void)
{
    if (!mutex_trylock(&n10_usb_q_lock)) return -EBUSY;
    if (n10_usb_q_owner && n10_usb_q_owner != current) {
        mutex_unlock(&n10_usb_q_lock);
        return -EBUSY;
    }
    return 0;
}
static void n10_usb_policy_exit(void) { mutex_unlock(&n10_usb_q_lock); }
static void n10_usb_quiesce_physical(unsigned long event)
{
    if (IS_VIRTUAL(event)) return;
    /* Policy commands emitted by this transaction are not physical cable events. */
    if (READ_ONCE(n10_usb_q_owner) == current &&
        (event == NOTIFY_EVENT_ALL_DISABLE || event == NOTIFY_EVENT_HOST_DISABLE ||
         event == NOTIFY_EVENT_CLIENT_DISABLE)) return;
    if ((check_event_type(event) & NOTIFY_EVENT_STATE) ||
        event == NOTIFY_EVENT_POWER_SOURCE || event == NOTIFY_EVENT_PD_CONTRACT ||
        event == NOTIFY_EVENT_VBUSPOWER || event == NOTIFY_EVENT_VBUS_RESET)
        atomic_inc(&n10_usb_q_epoch);
}
bool n10_usb_quiesce_off_requested(void)
{
    return READ_ONCE(n10_usb_q_owner) && READ_ONCE(n10_usb_q_off);
}
bool n10_usb_quiesce_owned(void) { return READ_ONCE(n10_usb_q_owner) != NULL; }
void n10_usb_quiesce_phy_error(bool off, int error)
{
    if (!READ_ONCE(n10_usb_q_owner) || !error) return;
    if (off) WRITE_ONCE(n10_usb_q_transition_error, error);
    else WRITE_ONCE(n10_usb_q_restore_error, error);
}
void n10_usb_quiesce_transition_error(int error)
{
    if (READ_ONCE(n10_usb_q_owner) && error)
        WRITE_ONCE(n10_usb_q_transition_error, error);
}

static int n10_usb_q_wait(struct usb_notify *u, bool off)
{
    atomic_t *done = off ? &n10_usb_q_begin_done : &n10_usb_q_end_done;
    struct work_struct *work = off ? &n10_usb_q_begin_work : &n10_usb_q_end_work;
    unsigned int attempts;
    int ret = -ETIMEDOUT;
    /* Queue ordering fences every prior notifier callback, including a late OFF.
     * The two persistent work objects are never reused while ownership is held. */
    if (!queue_work(u->notifier_wq, work)) return -EBUSY;
    for (attempts = 0; attempts < 200; ++attempts) {
        if (atomic_read(done) && !work_busy(work)) {
            ret = n10_exynos_usb_quiesce_check(off);
            if (ret != -EAGAIN) break;
        }
        msleep(10);
    }
    if (ret == -EAGAIN) ret = -ETIMEDOUT;
    return ret;
}

int n10_usb_quiesce_begin(struct n10_pm_result *out)
{
    struct otg_notify *n = get_otg_notify();
    struct usb_notify *u;
    int ret;
    if (!out || !n || !n->u_notify || !n->disable_control || !n->is_wakelock)
        return -EOPNOTSUPP;
    u = (struct usb_notify *)n->u_notify;
    if (!mutex_trylock(&n10_usb_q_lock)) return -EBUSY;
    if (n10_usb_q_owner || u->c_type != NOTIFY_EVENT_VBUS ||
        u->c_status != NOTIFY_EVENT_ENABLED ||
        u->ndev.mode != NOTIFY_PERIPHERAL_MODE ||
        u->typec_status.power_role != HNOTIFY_SINK ||
        u->disable_state != NOTIFY_BLOCK_TYPE_NONE || u->udev.disable_state ||
        is_host_cable_enable(n) || !n10_usb_q_wake_active(&u->ws)) {
        mutex_unlock(&n10_usb_q_lock);
        return -EBUSY;
    }
    n10_usb_q_expected_epoch = atomic_read(&n10_usb_q_epoch);
    ret = n10_exynos_usb_quiesce_check(false);
    if (ret) { mutex_unlock(&n10_usb_q_lock); return ret; }
    n10_usb_q_owner = current;
    n10_usb_q_notify = u;
    n10_usb_q_original_disable = u->disable_state;
    if (!++n10_usb_q_generation) ++n10_usb_q_generation;
    out->qgeneration = n10_usb_q_generation;
    out->usb_cookie = n10_usb_q_generation;
    out->cable_epoch = n10_usb_q_expected_epoch;
    n10_usb_q_transition_error = n10_usb_q_restore_error = 0;
    n10_usb_q_off = true;
    atomic_set(&n10_usb_q_begin_done, 0);
    atomic_set(&n10_usb_q_end_done, 0);
    mutex_unlock(&n10_usb_q_lock);
    ret = set_notify_disable(&u->udev, NOTIFY_BLOCK_TYPE_CLIENT);
    if (!ret) ret = n10_usb_q_wait(u, true);
    if (!ret && READ_ONCE(n10_usb_q_transition_error))
        ret = READ_ONCE(n10_usb_q_transition_error);
    if (!ret && (unsigned int)atomic_read(&n10_usb_q_epoch) != n10_usb_q_expected_epoch) ret = -ESTALE;
    if (!ret && (u->c_type != NOTIFY_EVENT_VBUS ||
        u->c_status != NOTIFY_EVENT_BLOCKED || u->ndev.mode != NOTIFY_NONE_MODE ||
        !is_client_cable_block(n) || n10_usb_q_wake_active(&u->ws))) ret = -EBUSY;
    return ret;
}

int n10_usb_quiesce_validate(void)
{
    struct usb_notify *u = READ_ONCE(n10_usb_q_notify);
    int ret;
    if (!u || READ_ONCE(n10_usb_q_owner) != current || !READ_ONCE(n10_usb_q_off))
        return -EPERM;
    if ((unsigned int)atomic_read(&n10_usb_q_epoch) != n10_usb_q_expected_epoch)
        return -ESTALE;
    ret = n10_exynos_usb_quiesce_check(true);
    if (!ret && (u->c_type != NOTIFY_EVENT_VBUS ||
        u->c_status != NOTIFY_EVENT_BLOCKED || u->ndev.mode != NOTIFY_NONE_MODE ||
        !is_client_cable_block(u->o_notify) || n10_usb_q_wake_active(&u->ws))) ret = -EBUSY;
    if (!ret && (unsigned int)atomic_read(&n10_usb_q_epoch) != n10_usb_q_expected_epoch)
        ret = -ESTALE;
    return ret;
}

int n10_usb_quiesce_end(struct n10_pm_result *out)
{
    struct usb_notify *u;
    int ret, epoch_error;
    if (!out) return -EINVAL;
    if (!mutex_trylock(&n10_usb_q_lock)) return -EBUSY;
    if (!n10_usb_q_owner || !out->usb_cookie || out->usb_cookie != n10_usb_q_generation) { mutex_unlock(&n10_usb_q_lock); return 0; }
    if (n10_usb_q_owner != current) { mutex_unlock(&n10_usb_q_lock); return -EPERM; }
    u = n10_usb_q_notify;
    n10_usb_q_off = false;
    if (!++n10_usb_q_generation) ++n10_usb_q_generation;
    out->qgeneration = n10_usb_q_generation;
    out->usb_cookie = n10_usb_q_generation;
    mutex_unlock(&n10_usb_q_lock);
    ret = set_notify_disable(&u->udev, n10_usb_q_original_disable);
    if (!ret) ret = n10_usb_q_wait(u, false);
    if (!ret && READ_ONCE(n10_usb_q_restore_error)) ret = READ_ONCE(n10_usb_q_restore_error);
    epoch_error = (unsigned int)atomic_read(&n10_usb_q_epoch) != n10_usb_q_expected_epoch ? -ESTALE : 0;
    if (!ret && u->disable_state != n10_usb_q_original_disable) ret = -EIO;
    if (!ret && !epoch_error && (u->c_type != NOTIFY_EVENT_VBUS ||
        u->c_status != NOTIFY_EVENT_ENABLED || u->ndev.mode != NOTIFY_PERIPHERAL_MODE ||
        !is_client_cable_enable(u->o_notify) || !n10_usb_q_wake_active(&u->ws))) ret = -EIO;
    if (!ret) {
        mutex_lock(&n10_usb_q_lock);
        n10_usb_q_owner = NULL;
        n10_usb_q_notify = NULL;
        mutex_unlock(&n10_usb_q_lock);
    }
    return ret ? ret : epoch_error;
}
