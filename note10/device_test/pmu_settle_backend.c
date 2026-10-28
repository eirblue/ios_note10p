/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after the PMU observer; caller holds pm_mutex. Reads only. */
#include <linux/note10_pmu_settle.h>
#include <linux/irqflags.h>
static unsigned int n10_settle_completed, n10_settle_next, n10_settle_failed;
int n10_pmu_settle_capture(struct n10_pmu_settle_sample *out,
                         unsigned int completed, unsigned int index)
{
    struct n10_pmu_noirq_sample baseline;
    unsigned int phase;
#ifdef CONFIG_EXYNOS_PMU
    unsigned int i, value;
#endif
    if (!out) return -EINVAL;
    memset(out, 0, sizeof(*out));
    out->completed = completed; out->index = index; out->error = 1;
    if (!completed || index >= 3 || irqs_disabled()) return -EINVAL;
    if (n10_pmu_noirq_read(&baseline, completed)) return -EIO;
    out->generation = baseline.generation;
    for (phase = 0; phase < 3; ++phase)
        if (n10_abox_pmu_samples[phase].seen != 1 || n10_abox_pmu_samples[phase].error ||
            n10_abox_pmu_samples[phase].phase != phase || n10_abox_pmu_samples[phase].count != 2 ||
            n10_abox_pmu_samples[phase].generation != baseline.generation) return -EIO;
    if (completed != n10_settle_completed) {
        if (index) return -EIO;
        n10_settle_completed = completed; n10_settle_next = 0; n10_settle_failed = 0;
    }
    if (n10_settle_failed || index != n10_settle_next) return -EIO;
    n10_settle_failed = 1;
#ifndef CONFIG_EXYNOS_PMU
    out->error = 2;
    return -EIO;
#else
    out->error = 3;
    if (IS_ERR_OR_NULL(exynos_get_pmu_regmap())) return -EIO;
    out->error = 4;
    for (i = 0; i < 16; ++i) {
        if (exynos_pmu_read(n10_pmu_domain_offsets[i][0], &value)) return -EIO;
        out->before |= (value & 1U) << i;
        if (exynos_pmu_read(n10_pmu_domain_offsets[i][1], &value)) return -EIO;
        out->state |= (value & 1U) << i;
        if (exynos_pmu_read(n10_pmu_domain_offsets[i][0], &value)) return -EIO;
        out->after |= (value & 1U) << i;
    }
    out->error = 0; ++n10_settle_next; n10_settle_failed = 0;
    return 0;
#endif
}
