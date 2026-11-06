/* SPDX-License-Identifier: GPL-2.0-only */
/* Same irreversible native ticket closure; no hardware while draining. */
#include <linux/preempt.h>
#include <linux/irqflags.h>
#include <linux/sched.h>
#include <linux/delay.h>
struct n141_snapshot { const char *entry; unsigned int depth,irq_state,self; };
static bool n141_account_locked(struct n141_snapshot *snapshot)
{
    u64 total=0;unsigned int index;
    memset(snapshot,0,sizeof(*snapshot));
    for(index=0;index<ARRAY_SIZE(n138_contexts);index++){
        struct n138_context *context=&n138_contexts[index];
        if(!context->depth){
            if(context->task || context->task_owned || context->entry)n138_history|=1;
            continue;
        }
        if(!context->task || !context->task_owned || !context->entry)n138_history|=1;
        total+=context->depth;
        if(!snapshot->depth || context->task==current){
            snapshot->entry=context->entry;snapshot->depth=context->depth;
            snapshot->irq_state=context->irq_state;snapshot->self=context->task==current;
        }
    }
    if(total!=n138_active || total>~0U)n138_history|=1;
    return !n138_history;
}
static int n141_close_error(const char *reason,int error)
{
    n138_detail.reason=reason;n138_detail.state=n138_active;
    n138_detail.aux=n138_history;n138_detail.value=error;return error;
}
static int n141_deadline_check(void)
{
    unsigned long flags;int error=0;
    spin_lock_irqsave(&n138_lock,flags);
    if(n138_history)error=n141_close_error("admission-history",-EBUSY);
    else if(!n138_polls || ktime_get_ns()>=n138_deadline)
        error=n141_close_error("aggregate-budget",-ETIMEDOUT);
    spin_unlock_irqrestore(&n138_lock,flags);return error;
}
static int n141_display_close(void)
{
    unsigned long flags;struct n141_snapshot snapshot={0};int error=0;
    unsigned int caller_count=preempt_count()&(PREEMPT_MASK|HARDIRQ_MASK|SOFTIRQ_MASK|NMI_MASK);
    bool caller_irq_off=irqs_disabled();
    spin_lock_irqsave(&n138_lock,flags);
    if(n138_seen){spin_unlock_irqrestore(&n138_lock,flags);return -EALREADY;}
    /* One unchanged total budget, including drain and every later native ACK. */
    n138_deadline=ktime_get_ns()+N138_BUDGET_NS;n138_polls=N138_POLL_LIMIT;
    n138_seen=true;n138_closed=true;n138_aborting=n138_active!=0;
    spin_unlock_irqrestore(&n138_lock,flags);
    for(;;){
        spin_lock_irqsave(&n138_lock,flags);
        if(!n141_account_locked(&snapshot))error=n141_close_error("admission-history",-EBUSY);
        else if(snapshot.self)error=n141_close_error("admission-self",-EBUSY);
        else if(caller_count || caller_irq_off)error=n141_close_error("admission-context",-EBUSY);
        else if(!n138_polls || ktime_get_ns()>=n138_deadline)
            error=n141_close_error("admission-timeout",-ETIMEDOUT);
        else if(!n138_active){
            /* No pre-existing context remains; no new one may enter. */
            n138_aborting=false;
            spin_unlock_irqrestore(&n138_lock,flags);return 0;
        }
        if(error){spin_unlock_irqrestore(&n138_lock,flags);break;}
        n138_polls--;
        spin_unlock_irqrestore(&n138_lock,flags);
        /* Known normal kexec task path, before core/native/CAL locks or IRQ
         * mutation. This is not a generic in_atomic() sleepability test. */
        cond_resched();udelay(10);
    }
    if(snapshot.depth)pr_emerg("N10XNU141 id=%s admission entry=%.64s depth=%u irq=%u self=%u\n",
        N10_KEXEC_BUILD_ID,snapshot.entry?snapshot.entry:"none",snapshot.depth,
        snapshot.irq_state,snapshot.self);
    /* Permanent closure and all poison/ticket depths retained on refusal. */
    return error;
}
