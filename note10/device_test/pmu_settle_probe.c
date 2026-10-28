/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/atomic.h>
#include <linux/workqueue.h>
#include <linux/jiffies.h>
#include <linux/note10_pmu_settle.h>
static atomic_t n10_settle_armed = ATOMIC_INIT(0);
static unsigned int n10_settle_generation, n10_settle_index;
static unsigned long n10_settle_start;
static const unsigned int n10_settle_targets[3] = {1000, 5000, 15000};
static void n10_settle_worker(struct work_struct *unused);
static DECLARE_DELAYED_WORK(n10_settle_work, n10_settle_worker);
static void n10_settle_record(struct n10_pmu_settle_sample *s,
                              unsigned int target, unsigned int elapsed, int status)
{
    unsigned int copy;
    char frame[384];
    for (copy = 0; copy < 4; ++copy) {
        int count = scnprintf(frame, sizeof(frame),
            "id=%s seq=%u generation=%u completed=%x index=%x target_ms=%x elapsed_ms=%x error=%u before=%x state=%x after=%x status=%u",
            N10_RESERVE_BUILD_ID, s->index * 4 + copy, s->generation, s->completed,
            s->index, target, elapsed, s->error, s->before, s->state, s->after, status ? 1 : 0);
        pr_info("N10PST1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    }
}
static void n10_settle_worker(struct work_struct *unused)
{
    struct n10_pmu_settle_sample sample = {0};
    unsigned int elapsed, target, wait;
    int status;
    (void)unused;
    if (n10_settle_index >= 3) return;
    target = n10_settle_targets[n10_settle_index];
    elapsed = jiffies_to_msecs(jiffies - n10_settle_start);
    if (elapsed < target) {
        if (schedule_delayed_work(&n10_settle_work, msecs_to_jiffies(target - elapsed))) return;
        memset(&sample, 0, sizeof(sample));sample.index = n10_settle_index;sample.error = 6;
        n10_settle_record(&sample, target, elapsed, -EIO);n10_settle_index = 3;return;
    }
    if (elapsed > 30000) {
        memset(&sample, 0, sizeof(sample));sample.index = n10_settle_index;sample.error = 7;
        n10_settle_record(&sample, target, elapsed, -EIO);n10_settle_index = 3;return;
    }
    status = n10_pm_settle_capture(&sample, n10_settle_generation, n10_settle_index);
    n10_settle_record(&sample, target, elapsed, status);
    if (status) { n10_settle_index = 3; return; }
    if (++n10_settle_index >= 3) return;
    elapsed = jiffies_to_msecs(jiffies - n10_settle_start);
    wait = elapsed < n10_settle_targets[n10_settle_index] ? n10_settle_targets[n10_settle_index] - elapsed : 1;
    if (!schedule_delayed_work(&n10_settle_work, msecs_to_jiffies(wait))) {
        sample.index = n10_settle_index;sample.error = 6;
        n10_settle_record(&sample, n10_settle_targets[n10_settle_index], elapsed, -EIO);
        n10_settle_index = 3;
    }
}
static void n10_arm_pmu_settle(unsigned int completed)
{
    struct n10_pmu_settle_sample sample;
    if (atomic_cmpxchg(&n10_settle_armed, 0, 1)) return;
    n10_settle_generation = completed;n10_settle_start = jiffies;
    if (!completed || !schedule_delayed_work(&n10_settle_work, msecs_to_jiffies(1000))) {
        memset(&sample, 0, sizeof(sample));sample.completed = completed;sample.error = 6;
        n10_settle_record(&sample, 1000, 0, -EIO);n10_settle_index = 3;
    }
}
