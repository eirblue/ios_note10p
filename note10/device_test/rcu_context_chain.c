/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in cpu_pm.c; record one bounded sample in the existing locked walk. */
#include <linux/note10_pm_preconditions.h>
#include <linux/note10_rcu_context_audit.h>
static struct n10_rcu_sample n10_rcu_last;
static int n10_rcu_bad, n10_rcu_attempted, n10_rcu_resolved, n10_rcu_checked;
void n10_rcu_begin(unsigned int generation)
{
    memset(&n10_rcu_last, 0, sizeof(n10_rcu_last));
    n10_rcu_bad = n10_rcu_attempted = n10_rcu_resolved = n10_rcu_checked = 0;
    n10_rcu_last.generation = generation; n10_rcu_last.seen = 1;
}
void n10_rcu_invalidate(void) { if (!n10_rcu_bad) n10_rcu_bad = -EIO; }
static int n10_rcu_fail(int error) { n10_rcu_invalidate(); return error; }
int n10_rcu_collect(const struct n10_precond_sample *pre, unsigned int generation)
{
    int ret;
    if (!n10_pre_context(generation, 1, 1) || in_interrupt()) return n10_rcu_fail(-EPERM);
    if (!pre || n10_rcu_bad || n10_rcu_attempted || n10_rcu_last.seen != 1 || n10_rcu_last.completed || n10_rcu_last.generation != generation || pre->generation != generation || pre->seen != 1 || pre->bad || pre->completed || pre->error || !pre->count || pre->count > N10_PRECOND_CAP) return n10_rcu_fail(-EIO);
    n10_rcu_attempted = 1;
    n10_rcu_last.row.chain_count = pre->count;
    ret = n10_rcu_get(&n10_rcu_last.row, generation);
    if (ret) return n10_rcu_fail(ret);
    n10_rcu_resolved = 1; n10_rcu_checked = 1; return 0;
}
void n10_rcu_finish(int error)
{
    if (n10_rcu_last.seen != 1 || n10_rcu_last.completed) { n10_rcu_invalidate(); return; }
    if (error) n10_rcu_invalidate();
    n10_rcu_last.error = error; n10_rcu_last.completed = 1;
}
int n10_rcu_copy(struct n10_rcu_sample *out, unsigned int completed)
{
    unsigned int next = n10_rcu_last.generation + 1; if (!next) next = 1;
    if (!out || !completed || n10_rcu_bad || !n10_rcu_attempted || !n10_rcu_resolved || !n10_rcu_checked || n10_rcu_last.seen != 1 || n10_rcu_last.completed != 1 || n10_rcu_last.error || next != completed) return -EIO;
    memcpy(out, &n10_rcu_last, sizeof(*out)); return 0;
}
