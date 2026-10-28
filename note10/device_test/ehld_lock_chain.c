/* SPDX-License-Identifier: GPL-2.0-only */
/* Included from cpu_pm.c; bounded lifecycle in the existing notifier walk. */
#include <linux/note10_pm_preconditions.h>
#include <linux/note10_ehld_lock_audit.h>
#include <linux/kernel.h>
static struct n10_ehld_lock_sample n10_ehld_lock_last;
static int n10_ehld_lock_bad, n10_ehld_lock_attempted, n10_ehld_lock_resolved, n10_ehld_lock_checked;
void n10_ehld_lock_begin(unsigned int generation)
{
	memset(&n10_ehld_lock_last, 0, sizeof(n10_ehld_lock_last));
	n10_ehld_lock_bad = n10_ehld_lock_attempted = n10_ehld_lock_resolved = n10_ehld_lock_checked = 0;
	n10_ehld_lock_last.generation = generation;
	n10_ehld_lock_last.seen = 1;
}
static int n10_ehld_lock_fail(int error)
{
	if (!n10_ehld_lock_bad)
		n10_ehld_lock_bad = error ? error : -EIO;
	return error ? error : -EIO;
}
void n10_ehld_lock_invalidate(void)
{
	(void)n10_ehld_lock_fail(-EIO);
}
int n10_ehld_lock_collect(struct notifier_block *n,
			  const struct n10_precond_sample *pre,
			  unsigned int index, unsigned int generation)
{
	int ret;
	if (!n10_pre_context(generation, 1, 1) || in_interrupt())
		return n10_ehld_lock_fail(-EPERM);
	if (n10_ehld_lock_bad ||
	    n10_ehld_lock_last.seen != 1 || n10_ehld_lock_last.completed ||
	    n10_ehld_lock_last.generation != generation || !pre ||
	    index >= pre->count || pre->count > N10_PRECOND_CAP)
		return n10_ehld_lock_fail(-EIO);
	if (pre->row[index].kind != N10_PRE_EHLD)
		return 0;
	if (n10_ehld_lock_attempted)
		return n10_ehld_lock_fail(-EIO);
	n10_ehld_lock_attempted = 1;
	n10_ehld_lock_last.row.index = index;
	ret = n10_ehld_lock_get(&n10_ehld_lock_last.row, n, pre, index, generation);
	if (ret)
		return n10_ehld_lock_fail(ret);
	n10_ehld_lock_resolved = 1;
	return 0;
}
int n10_ehld_lock_complete(const struct n10_precond_sample *pre,
			   unsigned int generation)
{
	struct n10_ehld_lock_row *row = &n10_ehld_lock_last.row;
	if (!pre || !n10_pre_context(generation, 1, 1) || in_interrupt() ||
	    n10_ehld_lock_bad || !n10_ehld_lock_attempted ||
	    !n10_ehld_lock_resolved || n10_ehld_lock_checked ||
	    n10_ehld_lock_last.generation != generation || pre->generation != generation ||
	    pre->seen != 1 || pre->bad || pre->completed || pre->error ||
	    !pre->count || pre->count > N10_PRECOND_CAP || row->index >= pre->count ||
	    pre->row[row->index].kind != N10_PRE_EHLD ||
	    pre->row[row->index].valid != 3 ||
	    pre->row[row->index].value[0] < INT_MIN ||
	    pre->row[row->index].value[0] > INT_MAX ||
	    row->running_valid != row->lock_available ||
	    row->running > 1 || (!row->running_valid && row->running))
		return n10_ehld_lock_fail(-EIO);
	row->chain_count = pre->count;
	n10_ehld_lock_checked = 1;
	return 0;
}
void n10_ehld_lock_finish(int error)
{
	if (n10_ehld_lock_last.seen != 1 || n10_ehld_lock_last.completed) {
		(void)n10_ehld_lock_fail(-EIO);
		return;
	}
	if (error || !n10_ehld_lock_checked)
		(void)n10_ehld_lock_fail(error);
	n10_ehld_lock_last.error = error;
	n10_ehld_lock_last.completed = 1;
}
int n10_ehld_lock_copy(struct n10_ehld_lock_sample *out, unsigned int completed)
{
	unsigned int next = n10_ehld_lock_last.generation + 1;
	if (!next)
		next = 1;
	if (!out || !completed || n10_ehld_lock_bad || !n10_ehld_lock_attempted ||
	    !n10_ehld_lock_resolved || !n10_ehld_lock_checked || n10_ehld_lock_last.seen != 1 ||
	    n10_ehld_lock_last.completed != 1 || n10_ehld_lock_last.error ||
	    next != completed)
		return -EIO;
	memcpy(out, &n10_ehld_lock_last, sizeof(*out));
	return 0;
}
