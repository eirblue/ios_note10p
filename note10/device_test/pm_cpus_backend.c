/* SPDX-License-Identifier: GPL-2.0-only */
/* Called only from the owned TEST_PLATFORM stop, with PM mutex and local IRQs on.
 * Original hotplug APIs always pair, including partial freeze failures. */
#include <linux/cpu.h>
#include <linux/note10_pm_cpus.h>
static struct n10_pm_cpus_sample n10_pm_cpus_last;
static unsigned int n10_pm_cpus_bits(void)
{
    unsigned long bits = READ_ONCE(cpumask_bits(cpu_online_mask)[0]);
    return bits & ~255UL ? 256 : (unsigned int)bits;
}
int n10_pm_cpus_roundtrip(unsigned int generation)
{
    struct n10_pm_cpus_sample *s = &n10_pm_cpus_last;
    struct n10_pmu_noirq_sample pmu;
    unsigned int completed = generation + 1;
    int result;
    if (!completed) completed = 1;
    if (!n10_pm_noirq_ready(PM_SUSPEND_MEM) || !generation ||
        generation != n10_pm_active->qgeneration) return -EPERM;
    if (s->seen && s->generation == generation) { s->bad = 1; return -EIO; }
    memset(s, 0, sizeof(*s));s->generation = generation;s->seen = 1;
    s->phase = n10_pm_active->qphase;s->before = n10_pm_cpus_bits();
    if (s->before != 255 || num_online_cpus() != 8 ||
        n10_pmu_noirq_read(&pmu, completed)) { s->error = -EIO; return -EIO; }
    s->attempted = 1;
    result = disable_nonboot_cpus();
    s->disabled = 1;s->original_error = result;s->stopped = n10_pm_cpus_bits();
    s->cpu = raw_smp_processor_id();
    if (!result && (s->stopped != 1 || num_online_cpus() != 1 || s->cpu || irqs_disabled()))
        result = -EIO;
    if (!result) {
        n10_pmu_cpu_capture(generation);
        if (n10_pmu_cpu_read(&pmu, completed)) result = -EIO;
    }
    /* Mandatory even when freeze_secondary_cpus failed part-way. */
    enable_nonboot_cpus();s->enabled = 1;s->restored = n10_pm_cpus_bits();
    if (s->restored != s->before || num_online_cpus() != 8 || irqs_disabled()) result = -EIO;
    s->error = result;
    return result;
}
int n10_pm_cpus_read(struct n10_pm_cpus_sample *out,
                     struct n10_pmu_noirq_sample *pmu, unsigned int completed)
{
    unsigned int following;
    int ret;
    if (!out || !pmu || !completed || irqs_disabled()) return -EINVAL;
    mutex_lock(&pm_mutex);
    memcpy(out, &n10_pm_cpus_last, sizeof(*out));
    ret = n10_pmu_cpu_read(pmu, completed);
    mutex_unlock(&pm_mutex);
    following = out->generation + 1;if (!following) following = 1;
    if (ret || !out->generation || following != completed || pmu->generation != out->generation ||
        out->seen != 1 || out->bad || out->attempted != 1 || out->disabled != 1 || out->enabled != 1 ||
        out->before != 255 || out->stopped != 1 || out->restored != 255 || out->cpu ||
        out->phase != N10_Q_PM_ENTERED || out->original_error || out->error) return -EIO;
    return 0;
}
