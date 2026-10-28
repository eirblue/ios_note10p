/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in the owned suspend TU. */
#include <linux/note10_pm_branch.h>
int n10_branch_read(struct n10_branch_sample *out,unsigned int completed)
{
    int ret;if(!out || !completed || irqs_disabled())return -EINVAL;
    mutex_lock(&pm_mutex);ret=n10_branch_copy(out,completed);mutex_unlock(&pm_mutex);
    return ret;
}
