/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in cpu_pm.c. Candidate remains local to the held chain lock. */
#include <linux/note10_pmu_control_audit.h>
#include <linux/note10_pm_preconditions.h>
static struct n10_ctl_sample n10_ctl_last;
static int n10_ctl_bad,n10_ctl_attempted,n10_ctl_resolved;
void n10_ctl_begin(unsigned int generation)
{
    memset(&n10_ctl_last,0,sizeof(n10_ctl_last));n10_ctl_bad=0;n10_ctl_attempted=0;n10_ctl_resolved=0;
    n10_ctl_last.generation=generation;n10_ctl_last.seen=1;
}
void n10_ctl_invalidate(void){if(!n10_ctl_bad)n10_ctl_bad=-EIO;}
int n10_ctl_resolve(struct n10_ctl_stage *s,unsigned int chain_count,unsigned int generation)
{
    int ret;
    if (!s || !n10_pre_context(generation,1,1) || in_interrupt()) return -EPERM;
    if (n10_ctl_bad || n10_ctl_attempted || n10_ctl_last.seen!=1 || n10_ctl_last.completed || n10_ctl_last.generation!=generation ||
        s->count!=1 || !s->candidate || s->index>=chain_count || chain_count>32) return -EIO;
    n10_ctl_attempted=1;
    n10_ctl_last.row.index=s->index;n10_ctl_last.row.chain_count=chain_count;
    ret=n10_ctl_backend(s->candidate,&n10_ctl_last.row,generation);if(!ret)n10_ctl_resolved=1;return ret;
}
void n10_ctl_finish(int error){n10_ctl_last.error=error;n10_ctl_last.completed=1;}
int n10_ctl_copy(struct n10_ctl_sample *out,unsigned int completed)
{
    unsigned int next=n10_ctl_last.generation+1;if(!next)next=1;
    if (!out || !completed || n10_ctl_bad || !n10_ctl_attempted || !n10_ctl_resolved || n10_ctl_last.seen!=1 || n10_ctl_last.completed!=1 || n10_ctl_last.error || next!=completed) return -EIO;
    memcpy(out,&n10_ctl_last,sizeof(*out));return 0;
}
