/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after the bound power-domain driver. No extra predicate/power call. */
#include <linux/spinlock.h>
#include <linux/string.h>
#include <linux/note10_abox_pmu.h>
static DEFINE_SPINLOCK(n10_fsys_lock);
static struct n10_fsys_pm_sample n10_fsys_history;
static struct exynos_pm_domain *n10_fsys_owner;
static void n10_fsys_inc(unsigned int *value)
{
    if (*value == ~0U) n10_fsys_history.invalid = 1;
    else ++*value;
}
void n10_fsys_note(struct exynos_pm_domain *pd, unsigned int event, int result)
{
    struct n10_fsys_pm_sample *h = &n10_fsys_history;
    unsigned long flags;
    if (!pd || pd->cal_pdid != 0xb138000eU) return;
    spin_lock_irqsave(&n10_fsys_lock, flags);
    if (!pd->name || strcmp(pd->name, "pd-fsys0a") ||
        pd->pd_control != cal_pd_control ||
        pd->power_down_ok != exynos_pd_power_down_ok_usb) {
        h->invalid = 1;
        goto out;
    }
    if (event == 1 && !n10_fsys_owner) n10_fsys_owner = pd;
    if (n10_fsys_owner != pd) { h->invalid = 1; goto out; }
    switch (event) {
    case 1: n10_fsys_inc(&h->registered); break;
    case 2:
        n10_fsys_inc(&h->gates);
        if (result) n10_fsys_inc(&h->allowed);
        else n10_fsys_inc(&h->denied);
        break;
    case 3: n10_fsys_inc(&h->skipped); h->last_skipped = 1; break;
    case 4:
        n10_fsys_inc(&h->controls);
        h->last_negative = result < 0;
        h->last_result = result < 0 ? (unsigned int)(-(long long)result) : (unsigned int)result;
        if (result) n10_fsys_inc(&h->control_errors);
        break;
    case 5: n10_fsys_inc(&h->completed); h->last_skipped = 0; break;
    case 6: n10_fsys_inc(&h->entries); break;
    case 7: n10_fsys_inc(&h->exits); break;
    default: h->invalid = 1; break;
    }
out:
    spin_unlock_irqrestore(&n10_fsys_lock, flags);
}
int n10_fsys_gate(struct exynos_pm_domain *pd)
{
    int result = pd->power_down_ok();
    n10_fsys_note(pd, 2, result);
    return result;
}
void n10_fsys_pm_read(struct n10_fsys_pm_sample *out)
{
    unsigned long flags;
    spin_lock_irqsave(&n10_fsys_lock, flags);
    memcpy(out, &n10_fsys_history, sizeof(*out));
    spin_unlock_irqrestore(&n10_fsys_lock, flags);
}
