/* SPDX-License-Identifier: GPL-2.0-only */
/* Included where the retained kernel declares the bounded terminal catalog. */
#include <linux/spinlock.h>
static DEFINE_SPINLOCK(n131_dma_lock);
int n130_dma_record(struct device *device,int result)
{
    unsigned long flags;unsigned int i;int answer=result;
    if(!device)return -ENODEV;
    if(READ_ONCE(n130_arm_state)!=2)return 0;
    spin_lock_irqsave(&n131_dma_lock,flags);
    for(i=0;i<n130_dma_count;i++)if(n130_dma[i].device==device){
        n130_dma[i].result=result;goto out;
    }
    if(n130_dma_count>=ARRAY_SIZE(n130_dma)){answer=-ENOSPC;goto out;}
    n130_dma[n130_dma_count].device=device;
    n130_dma[n130_dma_count++].result=result;
out:
    spin_unlock_irqrestore(&n131_dma_lock,flags);return answer;
}
int n131_dma_status(struct device *device)
{
    unsigned long flags;unsigned int i;int answer=-ENOENT;
    if(!device)return -ENODEV;
    spin_lock_irqsave(&n131_dma_lock,flags);
    for(i=0;i<n130_dma_count;i++)if(n130_dma[i].device==device){answer=n130_dma[i].result;break;}
    spin_unlock_irqrestore(&n131_dma_lock,flags);return answer;
}
int n130_dma_ready(struct device *device)
{return n131_dma_status(device)==0;}
void n131_gate_refused(const char *stage,int result,struct device *owner)
{
    pr_emerg("N10XNU131 id=%s stage=%.32s errno=%d owner=%.64s\n",
        N10_KEXEC_BUILD_ID,stage,result,owner?dev_name(owner):"none");
}
