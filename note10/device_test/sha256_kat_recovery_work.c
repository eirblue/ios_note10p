/* New scheduling connection only; included after the unchanged recovery/KAT C.
 * Recovery remains its existing independent non-freezable workqueue.
 * This prevents a sleeping crypto call from blocking the initcall chain.
 * It is not hard-lockup recovery or cancellation of a running crypto call.
 */
static struct workqueue_struct *n10_sha256_queue;
static atomic_t n10_sha256_started = ATOMIC_INIT(0);
static unsigned long n10_sha256_admission_deadline;
static void n10_sha256_worker(struct work_struct *work);
static DECLARE_DELAYED_WORK(n10_sha256_work, n10_sha256_worker);

static void n10_sha256_worker(struct work_struct *work)
{
    (void)work;
    /* Admission only. Never flush, cancel or join this job from recovery. */
    if (atomic_read(&n10_return_requested) ||
        time_after_eq(jiffies, n10_sha256_admission_deadline)) {
        pr_info("N10SHACTL1 skipped admission\n");
        return;
    }
    if (READ_ONCE(system_state) != SYSTEM_RUNNING) {
        if (!queue_delayed_work(n10_sha256_queue, &n10_sha256_work,
                                msecs_to_jiffies(1000)))
            pr_info("N10SHACTL1 skipped requeue\n");
        return;
    }
    /* This function and its constants are permanent, not reclaimed __init text.
     * A stuck call does not occupy the recovery queue or hold the init task.
     * Scheduler/kernel progress is still required by the existing baseline. */
    (void)n10_sha256_kat_init();
}

static int __init n10_sha256_recovery_init(void)
{
    if (atomic_cmpxchg(&n10_sha256_started, 0, 1))
        return 0;
    /* Exact existing arm function: cycle gate, queue and 90-second delay unchanged. */
    if (n10_arm_auto_return())
        return 0;
    n10_sha256_admission_deadline = jiffies + msecs_to_jiffies(60000);
    n10_sha256_queue = alloc_workqueue("n10_sha256", WQ_UNBOUND | WQ_MEM_RECLAIM, 1);
    if (!n10_sha256_queue) {
        pr_info("N10SHACTL1 skipped allocation\n");
        return 0;
    }
    if (!queue_delayed_work(n10_sha256_queue, &n10_sha256_work, msecs_to_jiffies(1000))) {
        /* No job was queued; this fresh empty queue can be released safely. */
        destroy_workqueue(n10_sha256_queue);
        n10_sha256_queue = NULL;
        pr_info("N10SHACTL1 skipped queue\n");
    }
    return 0;
}
late_initcall(n10_sha256_recovery_init);
