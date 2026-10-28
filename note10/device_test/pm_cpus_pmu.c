/* SPDX-License-Identifier: GPL-2.0-only */
/* Separate CPU-stop bank. Existing successful noirq bank is a prerequisite. */
#include <linux/note10_pm_cpus.h>
static struct n10_pmu_noirq_sample n10_pmu_cpu_last;
void n10_pmu_cpu_capture(unsigned int generation)
{
    struct n10_pmu_noirq_sample *s = &n10_pmu_cpu_last, baseline;
    unsigned int completed = generation + 1;
#ifdef CONFIG_EXYNOS_PMU
    unsigned int i,value;
#endif
    if (!completed) completed = 1;
    if (s->seen && s->generation == generation) { ++s->seen;s->error = 1;return; }
    memset(s,0,sizeof(*s));s->generation = generation;s->seen = 1;s->error = 2;
    if (!generation || irqs_disabled() || n10_pmu_noirq_read(&baseline, completed)) return;
#ifndef CONFIG_EXYNOS_PMU
    s->error = 3;return;
#else
    s->error = 4;
    if (IS_ERR_OR_NULL(exynos_get_pmu_regmap())) return;
    s->error = 5;
    for (i = 0; i < 16; ++i) {
        if (exynos_pmu_read(n10_pmu_domain_offsets[i][0], &value)) return;
        s->before |= (value & 1U) << i;
        if (exynos_pmu_read(n10_pmu_domain_offsets[i][1], &value)) return;
        s->state |= (value & 1U) << i;
        if (exynos_pmu_read(n10_pmu_domain_offsets[i][0], &value)) return;
        s->after |= (value & 1U) << i;
    }
    s->error = 0;
#endif
}
int n10_pmu_cpu_read(struct n10_pmu_noirq_sample *out, unsigned int completed)
{
    unsigned int following;
    if (!out || !completed) return -EINVAL;
    memcpy(out,&n10_pmu_cpu_last,sizeof(*out));following = out->generation + 1;
    if (!following) following = 1;
    if (!out->generation || following != completed || out->seen != 1 || out->error ||
        ((out->before | out->state | out->after) & ~65535U)) return -EIO;
    return 0;
}
