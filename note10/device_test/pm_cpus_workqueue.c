/* SPDX-License-Identifier: GPL-2.0-only */
/* Keep a CPU-hotplug caller independent of a bound CPU worker pool. */
#ifdef CONFIG_NOTE10_PM_CPUS_TEST
static struct workqueue_struct *n10_pm_cpus_queue;
#endif
static bool n10_pm_cpus_schedule(unsigned long delay)
{
#ifdef CONFIG_NOTE10_PM_CPUS_TEST
    if (!n10_pm_cpus_queue) {
        n10_pm_cpus_queue = alloc_workqueue("n10_pm_cpus", WQ_UNBOUND | WQ_MEM_RECLAIM, 1);
        if (!n10_pm_cpus_queue) return false;
    }
    return queue_delayed_work(n10_pm_cpus_queue, &n10_pm_work, delay);
#else
    return schedule_delayed_work(&n10_pm_work, delay);
#endif
}
