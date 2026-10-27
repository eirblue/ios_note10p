/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after the bound core driver. No PMU write/update or power request. */
#include <linux/err.h>
#include <linux/errno.h>
#include <linux/of_platform.h>
#include <linux/string.h>
#include <linux/note10_abox_pmu.h>
#include <soc/samsung/exynos-pmu.h>
struct regmap;
extern struct regmap *exynos_get_pmu_regmap(void);
static struct n10_abox_pmu_sample n10_abox_pmu_samples[3];
static const unsigned int n10_abox_pmu_allowed[2][6] = {
    {0x2d80, 1, 0x2da0, 1, 0x2da4, 0x11},
    {0x2e00, 1, 0x2e20, 1, 0x2e24, 1},
};

void n10_abox_pmu_capture(unsigned int phase, unsigned int generation)
{
    struct n10_abox_pmu_sample *s;
#ifdef CONFIG_EXYNOS_PMU
    struct platform_device *parent = NULL, *cores[2] = {NULL, NULL};
    struct device_node *node, *child;
    bool parent_locked = false, locked[2] = {false, false};
    unsigned int i, id, children = 0, found = 0, tuple[6], value;
    int ret;
#endif
    if (phase >= 3) return;
    if (!phase && (!n10_abox_pmu_samples[0].seen || n10_abox_pmu_samples[0].generation != generation))
        memset(n10_abox_pmu_samples, 0, sizeof(n10_abox_pmu_samples));
    s = &n10_abox_pmu_samples[phase];
    if (s->seen++) { s->error = 1; return; }
    s->phase = phase; s->generation = generation; s->error = 2;
    if (!generation || (phase && (n10_abox_pmu_samples[phase - 1].seen != 1 ||
        n10_abox_pmu_samples[phase - 1].generation != generation))) return;
#ifndef CONFIG_EXYNOS_PMU
    /* The vendor disabled-config stub returns success without filling a value. */
    s->error = 3;
    return;
#else
    s->error = 4;
    node = of_find_compatible_node(NULL, NULL, "samsung,abox");
    if (!node) return;
    parent = of_find_device_by_node(node); of_node_put(node);
    if (!parent) return;
    s->error = 5;
    if (!device_trylock(&parent->dev)) goto out;
    parent_locked = true;
    if (!parent->dev.driver || !parent->dev.driver->name || strcmp(parent->dev.driver->name, "samsung-abox")) goto out;
    s->error = 6;
    for_each_available_child_of_node(parent->dev.of_node, child) {
        if (++children > 64) goto child_error;
        if (!of_device_is_compatible(child, "samsung,abox-core")) continue;
        if (of_property_read_u32(child, "samsung,id", &id) || id >= 2 || (found & (1U << id))) goto child_error;
        if (of_property_read_u32_array(child, "samsung,pmu_power", tuple, 2) ||
            of_property_read_u32_array(child, "samsung,pmu_enable", tuple + 2, 2) ||
            of_property_read_u32_array(child, "samsung,pmu_standby", tuple + 4, 2) ||
            memcmp(tuple, n10_abox_pmu_allowed[id], sizeof(tuple))) goto child_error;
        cores[id] = of_find_device_by_node(child);
        if (!cores[id]) goto child_error;
        if (!device_trylock(&cores[id]->dev)) goto child_error;
        locked[id] = true;
        if (cores[id]->dev.driver != &samsung_abox_core_driver.driver ||
            cores[id]->dev.parent != &parent->dev || cores[id]->dev.of_node != child) goto child_error;
        found |= 1U << id;
        ++s->count;
    }
    if (found != 3 || s->count != 2) goto out;
    s->error = 7;
    if (IS_ERR_OR_NULL(exynos_get_pmu_regmap())) goto out;
    /* Validate every device and tuple before the first read. PM-list lock is absent. */
    s->error = 8;
    for (i = 0; i < 2; ++i) {
        ret = exynos_pmu_read(n10_abox_pmu_allowed[i][0], &value);
        if (ret) goto out;
        s->power[i] = value & n10_abox_pmu_allowed[i][1];
        ret = exynos_pmu_read(n10_abox_pmu_allowed[i][2], &value);
        if (ret) goto out;
        s->enable[i] = value & n10_abox_pmu_allowed[i][3];
        ret = exynos_pmu_read(n10_abox_pmu_allowed[i][4], &value);
        if (ret) goto out;
        s->standby[i] = value & n10_abox_pmu_allowed[i][5];
    }
    s->error = 0;
    goto out;
child_error:
    of_node_put(child);
out:
    for (i = 0; i < 2; ++i) {
        if (locked[i]) device_unlock(&cores[i]->dev);
        if (cores[i]) put_device(&cores[i]->dev);
    }
    if (parent_locked) device_unlock(&parent->dev);
    put_device(&parent->dev);
#endif
}

int n10_abox_pmu_read(struct n10_abox_pmu_sample *out, unsigned int completed)
{
    unsigned int phase, next;
    if (!out || !completed) return -EINVAL;
    memcpy(out, n10_abox_pmu_samples, sizeof(n10_abox_pmu_samples));
    next = out[0].generation + 1;
    if (!next) next = 1;
    if (!out[0].generation || next != completed) return -EIO;
    for (phase = 0; phase < 3; ++phase)
        if (out[phase].seen != 1 || out[phase].error || out[phase].count != 2 ||
            out[phase].phase != phase || out[phase].generation != out[0].generation) return -EIO;
    return 0;
}
