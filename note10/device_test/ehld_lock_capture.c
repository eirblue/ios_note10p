/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_ehld_lock_audit.h>
int n10_ehld_lock_read(struct n10_ehld_lock_sample *out,
		      unsigned int completed)
{
	int ret;
	if (!out || !completed || irqs_disabled())
		return -EINVAL;
	mutex_lock(&pm_mutex);
	ret = n10_ehld_lock_copy(out, completed);
	mutex_unlock(&pm_mutex);
	return ret;
}
