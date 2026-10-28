/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in cpu_pm.c; writes occur only during the existing chain walk. */
#include <linux/note10_pm_branch.h>
static struct n10_branch_sample n10_branch_last;
static int n10_branch_bad;
void n10_branch_invalidate(void){if(!n10_branch_bad)n10_branch_bad=-EIO;}
void n10_branch_begin(unsigned int generation)
{
    memset(&n10_branch_last,0,sizeof(n10_branch_last));n10_branch_bad=0;
    n10_branch_last.generation=generation;n10_branch_last.seen=1;
}
int n10_branch_collect(struct notifier_block *n,unsigned int index,unsigned int kind)
{
    struct n10_branch_row *r;int ret;
    if(index>=N10_BRANCH_CAP || index!=n10_branch_last.count || kind>6)return -EIO;
    r=&n10_branch_last.row[index];r->index=index;r->kind=kind;n10_branch_last.count++;
    if(kind!=5)return 0;
    ret=n10_branch_pmu(n,r);return ret==1?0:ret<0?ret:-EIO;
}
void n10_branch_finish(int error){n10_branch_last.error=error;n10_branch_last.completed=1;}
int n10_branch_copy(struct n10_branch_sample *out,unsigned int completed)
{
    unsigned int next=n10_branch_last.generation+1;if(!next)next=1;
    if(!out || !completed || n10_branch_bad || n10_branch_last.seen!=1 || n10_branch_last.completed!=1 || n10_branch_last.error || next!=completed || n10_branch_last.count>N10_BRANCH_CAP)return -EIO;
    memcpy(out,&n10_branch_last,sizeof(*out));return 0;
}
