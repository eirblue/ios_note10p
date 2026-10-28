/* SPDX-License-Identifier: GPL-2.0-only */
/* Read the finished RAM sample under the existing owned suspend mutex. */
#include <linux/note10_pmu_state_audit.h>
int n10_state_read(struct n10_state_sample *out,unsigned int completed)
{
    int ret;if(!out || !completed || irqs_disabled())return -EINVAL;
    mutex_lock(&pm_mutex);ret=n10_state_copy(out,completed);mutex_unlock(&pm_mutex);
    return ret;
}
