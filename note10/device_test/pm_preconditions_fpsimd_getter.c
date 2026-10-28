/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in fpsimd.c; copy only local RAM state. */
#include <linux/note10_pm_preconditions.h>
int n10_pre_fpsimd(struct notifier_block *n, struct n10_precond_row *r)
{
    if (n != &fpsimd_cpu_pm_notifier_block || READ_ONCE(n->notifier_call) != fpsimd_cpu_pm_notifier) return 0;
    r->valid=15; r->value[0]=!!current->mm; r->value[1]=!!test_thread_flag(TIF_FOREIGN_FPSTATE);
    r->value[2]=atomic_read(&current->thread.fpsimd_kernel_state.depth);
    r->value[3]=__this_cpu_read(fpsimd_last_state)==&current->thread.fpsimd_state;
    return 1;
}
