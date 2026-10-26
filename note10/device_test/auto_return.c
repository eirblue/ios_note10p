/* SPDX-License-Identifier: GPL-2.0-only */
/* Opt-in one-shot recovery request. Dedicated, non-freezable workqueue.
 * No hard-lockup guarantee and no block-device writes by this extension.
 */
#include <linux/atomic.h>
#include <linux/reboot.h>
#include <linux/workqueue.h>
#include <linux/jiffies.h>

static volatile char n10_cycle[33] = "N10_CYCLE_SLOT_UNSET_0123456789A";
static atomic_t n10_return_started = ATOMIC_INIT(0);
static atomic_t n10_return_requested = ATOMIC_INIT(0);
static unsigned int n10_return_waits;
static struct workqueue_struct *n10_return_queue;
static void n10_return_worker(struct work_struct *unused);
static DECLARE_DELAYED_WORK(n10_return_work, n10_return_worker);

static int n10_cycle_valid(void)
{
    unsigned int i;
    for (i = 0; i < 32; ++i)
        if (!((n10_cycle[i] >= '0' && n10_cycle[i] <= '9') ||
              (n10_cycle[i] >= 'a' && n10_cycle[i] <= 'f')))
            return 0;
    return n10_cycle[32] == 0;
}

static void n10_return_record(unsigned int phase, unsigned int status)
{
    unsigned int sequence;
    char frame[256];
    for (sequence = 0; sequence < 16; ++sequence) {
        int count = scnprintf(frame, sizeof(frame),
            "id=%s cycle=%s phase=%u seq=%u delay_ms=90000 status=%u",
            N10_RESERVE_BUILD_ID, n10_cycle_valid() ? (const char *)n10_cycle : "00000000000000000000000000000000",
            phase, sequence, status);
        pr_info("N10RET1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    }
}

static void n10_return_worker(struct work_struct *unused)
{
    (void)unused;
    if (atomic_read(&n10_return_requested))
        return;
    if (system_state != SYSTEM_RUNNING) {
        if (++n10_return_waits < 30) {
            queue_delayed_work(n10_return_queue, &n10_return_work, msecs_to_jiffies(1000));
            return;
        }
        n10_return_record(3, 1);
        return;
    }
    if (atomic_cmpxchg(&n10_return_requested, 0, 1))
        return;
    n10_return_record(1, 0);
    kernel_restart("recovery");
    /* A successful restart does not return. Never request a second reboot. */
    n10_return_record(2, 1);
}

static int n10_arm_auto_return(void)
{
    if (atomic_cmpxchg(&n10_return_started, 0, 1))
        return -EBUSY;
    if (!n10_cycle_valid()) {
        n10_return_record(3, 2);
        return -EINVAL;
    }
    n10_return_queue = alloc_workqueue("n10_recovery", WQ_UNBOUND | WQ_MEM_RECLAIM, 1);
    if (!n10_return_queue) {
        n10_return_record(3, 3);
        return -ENOMEM;
    }
    if (!queue_delayed_work(n10_return_queue, &n10_return_work, msecs_to_jiffies(90000))) {
        n10_return_record(3, 4);
        return -EBUSY;
    }
    n10_return_record(0, 0);
    return 0;
}
