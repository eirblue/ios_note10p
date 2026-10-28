/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after original pre-PM timer samples. Read-only post-hotplug check. */
struct n10_pm_cpu_timer_sample { u64 value, frequency; unsigned int seen; };
static struct n10_pm_cpu_timer_sample n10_pm_cpu_timers[8];
static unsigned int n10_pm_cpu_timer_bad;
static void n10_pm_cpu_timer_read(void *unused)
{
    unsigned int cpu = smp_processor_id();
    struct n10_pm_cpu_timer_sample *s;
    (void)unused;
    if (cpu >= 8) { n10_pm_cpu_timer_bad = 1; return; }
    s = &n10_pm_cpu_timers[cpu];
    ++s->seen;s->value = read_sysreg(cntkctl_el1);s->frequency = read_sysreg(cntfrq_el0);
}
static void n10_report_pm_cpu_timers(unsigned int completed)
{
    unsigned int cpu, copy, status = !completed || !n10_timer_done;
    char frame[320];
    memset(n10_pm_cpu_timers,0,sizeof(n10_pm_cpu_timers));n10_pm_cpu_timer_bad = 0;
    if (!status) {
        cpus_read_lock();
        if (n10_online_bits() != 255 || num_online_cpus() != 8) status = 1;
        else on_each_cpu(n10_pm_cpu_timer_read, NULL, 1);
        cpus_read_unlock();
    }
    for (copy = 0; copy < 4; ++copy) {
        for (cpu = 0; cpu < 8; ++cpu) {
            struct n10_pm_cpu_timer_sample *s = &n10_pm_cpu_timers[cpu];
            unsigned int failed = status || n10_pm_cpu_timer_bad || s->seen != 1 ||
                n10_timers[cpu].seen != 1 || s->value != n10_timers[cpu].restored || s->frequency != 26000000;
            int count = scnprintf(frame,sizeof(frame),
                "id=%s seq=%u generation=%u cpu=%u pre_seen=%x seen=%x before=%llx after=%llx freq=%llx status=%u",
                N10_RESERVE_BUILD_ID,copy,completed,cpu,n10_timers[cpu].seen,s->seen,
                (unsigned long long)n10_timers[cpu].restored,(unsigned long long)s->value,
                (unsigned long long)s->frequency,failed?1:0);
            pr_info("N10NCT1 %s checksum=%08x\n",frame,n10_frame_checksum(frame,count));
        }
    }
}
