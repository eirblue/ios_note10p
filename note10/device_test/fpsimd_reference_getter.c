/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in pinned fpsimd.c; never dereference or export the reference. */
#include <linux/note10_fpsimd_reference_audit.h>
#include <linux/note10_pm_preconditions.h>
int n10_fps_get(struct notifier_block *n, struct n10_fps_row *row, unsigned int generation)
{
    struct fpsimd_state *last; int depth;
    if (!row || !n10_pre_context(generation, 1, 1) || in_interrupt()) return -EPERM;
    if (n != &fpsimd_cpu_pm_notifier_block || READ_ONCE(n->notifier_call) != fpsimd_cpu_pm_notifier) return -EIO;
    depth = atomic_read(&current->thread.fpsimd_kernel_state.depth);
    if (depth < 0) return -EIO;
    last = __this_cpu_read(fpsimd_last_state);
    row->reference = !last ? 0 : last == &current->thread.fpsimd_state ? 1 : 2;
    row->mm = !!current->mm;
    row->foreign = !!test_thread_flag(TIF_FOREIGN_FPSTATE);
    row->depth = (unsigned int)depth;
    return 0;
}
