/* SPDX-License-Identifier: GPL-2.0-only */
/* Runs inside the existing notifier registration lock and single chain walk. */
#include <linux/note10_pmu_state_audit.h>
static struct n10_state_sample n10_state_last;
static int n10_state_bad;
void n10_state_invalidate(void){if(!n10_state_bad)n10_state_bad=-EIO;}
void n10_state_begin(unsigned int generation)
{
    memset(&n10_state_last,0,sizeof(n10_state_last));n10_state_bad=0;
    n10_state_last.generation=generation;n10_state_last.seen=1;
}
int n10_state_collect(struct notifier_block *n,unsigned int index,unsigned int kind,unsigned int generation)
{
    struct n10_state_row *r;int ret;
    if(!n10_pre_context(generation,1,1) || in_interrupt())return -EPERM;
    if(n10_state_bad || n10_state_last.seen!=1 || n10_state_last.completed || index>=N10_STATE_CAP || index!=n10_state_last.count || kind>6 || n10_state_last.generation!=generation)return -EIO;
    r=&n10_state_last.row[index];r->index=index;r->kind=kind;n10_state_last.count++;
    if(kind!=5)return 0;
    ret=n10_state_pmu(n,r,generation);return ret==1?0:ret<0?ret:-EIO;
}
void n10_state_finish(int error){n10_state_last.error=error;n10_state_last.completed=1;}
int n10_state_copy(struct n10_state_sample *out,unsigned int completed)
{
    unsigned int next=n10_state_last.generation+1;if(!next)next=1;
    if(!out || !completed || n10_state_bad || n10_state_last.seen!=1 || n10_state_last.completed!=1 || n10_state_last.error || next!=completed || n10_state_last.count>N10_STATE_CAP)return -EIO;
    memcpy(out,&n10_state_last,sizeof(*out));return 0;
}
