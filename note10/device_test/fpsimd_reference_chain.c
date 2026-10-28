/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in cpu_pm.c; collect in the existing locked notifier walk. */
#include <linux/note10_fpsimd_reference_audit.h>
#include <linux/note10_pm_preconditions.h>
static struct n10_fps_sample n10_fps_last;
static int n10_fps_bad, n10_fps_attempted, n10_fps_resolved, n10_fps_checked;
void n10_fps_begin(unsigned int generation)
{
    memset(&n10_fps_last, 0, sizeof(n10_fps_last));
    n10_fps_bad = n10_fps_attempted = n10_fps_resolved = n10_fps_checked = 0;
    n10_fps_last.generation = generation; n10_fps_last.seen = 1;
}
void n10_fps_invalidate(void) { if (!n10_fps_bad) n10_fps_bad = -EIO; }
static int n10_fps_fail(int error) { n10_fps_invalidate(); return error; }
int n10_fps_collect(struct notifier_block *n, unsigned int index, unsigned int kind, unsigned int generation)
{
    int ret;
    if (!n10_pre_context(generation, 1, 1) || in_interrupt()) return n10_fps_fail(-EPERM);
    if (n10_fps_bad || n10_fps_last.seen != 1 || n10_fps_last.completed || n10_fps_last.generation != generation || index >= N10_PRECOND_CAP) return n10_fps_fail(-EIO);
    if (kind != N10_PRE_FPSIMD) return 0;
    if (n10_fps_attempted) return n10_fps_fail(-EIO);
    n10_fps_attempted = 1;
    n10_fps_last.row.index = index; n10_fps_last.row.kind = kind;
    ret = n10_fps_get(n, &n10_fps_last.row, generation);
    if (ret) return n10_fps_fail(ret);
    n10_fps_resolved = 1; return 0;
}
int n10_fps_complete(const struct n10_precond_sample *pre, unsigned int generation)
{
    const struct n10_precond_row *old; struct n10_fps_row *row = &n10_fps_last.row;
    if (!n10_pre_context(generation, 1, 1) || in_interrupt()) return n10_fps_fail(-EPERM);
    if (!pre || n10_fps_bad || n10_fps_checked || !n10_fps_attempted || !n10_fps_resolved || n10_fps_last.seen != 1 || n10_fps_last.completed || n10_fps_last.generation != generation || pre->generation != generation || pre->seen != 1 || pre->error || pre->count > N10_PRECOND_CAP || row->index >= pre->count) return n10_fps_fail(-EIO);
    old = &pre->row[row->index];
    if (old->kind != N10_PRE_FPSIMD || row->kind != old->kind || old->valid != 15 || old->value[0] != row->mm || old->value[1] != row->foreign || old->value[2] != row->depth || old->value[3] != (row->reference == 1)) return n10_fps_fail(-EIO);
    row->chain_count = pre->count; n10_fps_checked = 1; return 0;
}
void n10_fps_finish(int error)
{
    if (n10_fps_last.seen != 1 || n10_fps_last.completed) { n10_fps_invalidate(); return; }
    if (error) n10_fps_invalidate();
    n10_fps_last.error = error; n10_fps_last.completed = 1;
}
int n10_fps_copy(struct n10_fps_sample *out, unsigned int completed)
{
    unsigned int next = n10_fps_last.generation + 1; if (!next) next = 1;
    if (!out || !completed || n10_fps_bad || !n10_fps_attempted || !n10_fps_resolved || !n10_fps_checked || n10_fps_last.seen != 1 || n10_fps_last.completed != 1 || n10_fps_last.error || next != completed) return -EIO;
    memcpy(out, &n10_fps_last, sizeof(*out)); return 0;
}
