/* SPDX-License-Identifier: GPL-2.0-only */
/* Same pinned G2D driver TU; real probe resources, no name-based admission. */
#include <linux/clk-provider.h>
#include <linux/v130_kernel_api.h>
#include <linux/note10_legacy_kexec_build.h>
#if !defined(CONFIG_NOTE10_XNU_KEXEC_HANDOFF) || CONFIG_NOTE10_XNU_KEXEC_HANDOFF != 1
#error "G2D terminal proof requires the actual enabled handoff profile"
#endif

struct n132_g2d_detail {
    const char *reason;
    unsigned int item;
    unsigned long state;
    int value;
};
static void n132_g2d_detail_log(const struct n132_g2d_detail *detail,struct device *owner)
{
    pr_emerg("N10XNU132 id=%s g2d reason=%.24s item=%u state=%lu value=%d owner=%.64s\n",
        N10_KEXEC_BUILD_ID,detail->reason?detail->reason:"none",detail->item,detail->state,detail->value,owner?dev_name(owner):"none");
}
/* Caller holds the native task/admission lock. Capture the first inspected
 * predicate only; no extra register or timer read is needed for logging. */
static int n132_g2d_state_locked(struct g2d_device *g2d,struct n132_g2d_detail *detail)
{
    struct g2d_task *task;unsigned int count=0;unsigned long state=g2d->state;
    detail->reason=NULL;detail->item=0;detail->state=state;detail->value=0;
    if(!g2d->n132_terminal){detail->reason="not-terminal";return -EBUSY;}
    if(!test_bit(G2D_DEVICE_STATE_SUSPEND,&state)){detail->reason="not-suspended";return -EBUSY;}
    if(g2d->n132_ever_allocated){detail->reason="allocation-history";detail->value=1;return -EBUSY;}
    if(!list_empty(&g2d->tasks_active)){detail->reason="active-list";detail->value=1;return -EBUSY;}
    if(!list_empty(&g2d->tasks_prepared)){detail->reason="prepared-list";detail->value=1;return -EBUSY;}
    for(task=g2d->tasks;task;task=task->next){
        detail->item=count;
        if(count++>=G2D_MAX_JOBS){detail->reason="pool-bound";detail->state=0;detail->value=G2D_MAX_JOBS;return -EBUSY;}
        state=task->state;detail->state=state;
        /* Pinned native is_task_state_idle is exactly task->state == 0. */
        if(state){detail->reason="task-state";return -EBUSY;}
        if(timer_pending(&task->fence_timer)){detail->reason="fence-timer";detail->value=1;return -EBUSY;}
        if(timer_pending(&task->hw_timer)){detail->reason="hw-timer";detail->value=1;return -EBUSY;}
    }
    if(count!=G2D_MAX_JOBS){detail->reason="pool-size";detail->item=count;detail->state=0;return -ENODEV;}
    return 0;
}

static void n132_g2d_shutdown(struct platform_device *pdev)
{
    struct device *device=&pdev->dev;struct g2d_device *g2d=platform_get_drvdata(pdev);
    unsigned long flags;unsigned int job;int error;const char *stage="g2d-provider";
    struct n132_g2d_detail detail={"provider",0,0,0};
    if(!g2d || g2d->dev!=device){n131_gate_refused(stage,-ENODEV,device);n132_g2d_detail_log(&detail,device);return;}
    stage="g2d-record";error=n130_dma_record(device,-EINPROGRESS);
    if(error!=-EINPROGRESS){if(!error)error=-EPERM;detail.reason="catalog-pending";detail.value=error;goto refused;}
    stage="g2d-tasks";
    spin_lock_irqsave(&g2d->lock_task,flags);
    if(g2d->n132_terminal){error=-EALREADY;detail.reason="duplicate-shutdown";detail.value=1;}
    else{
        g2d->n132_terminal=true;
        set_bit(G2D_DEVICE_STATE_SUSPEND,&g2d->state);
        error=n132_g2d_state_locked(g2d,&detail);
    }
    spin_unlock_irqrestore(&g2d->lock_task,flags);
    if(error)goto refused;
    detail.item=0;detail.state=0;detail.value=0;
    stage="g2d-resources";
    error=-ENODEV;
    if(!g2d->schedule_workq){detail.reason="queue-resource";goto refused;}
    if(!g2d->reg){detail.reason="mmio-resource";goto refused;}
    if(IS_ERR_OR_NULL(g2d->clock)){detail.reason="clock-resource";goto refused;}
    if(!g2d->n132_irq){detail.reason="irq-resource";goto refused;}
    /* No allocation has ever occurred: no starter/fence/scheduler ownership.
     * Freeze prevents future allocations; drain the real scheduler and IRQ. */
    flush_workqueue(g2d->schedule_workq);
    disable_irq_nosync(g2d->n132_irq);synchronize_irq(g2d->n132_irq);
    stage="g2d-power";error=pm_runtime_get_sync(device);
    if(error<0){pm_runtime_put_noidle(device);detail.reason="pm-get";detail.value=error;goto refused;}
    pm_runtime_forbid(device);
    if(pm_runtime_suspended(device)){error=-EIO;detail.reason="pm-suspended";detail.value=1;goto refused;}
    stage="g2d-clock";error=clk_prepare_enable(g2d->clock);
    if(error<0){detail.reason="clock-prepare";detail.value=error;goto refused;}
    /* Live PM/owned clock make the actual native readbacks accessible.
     * No reset, kill, job push or unqualified translation disable. */
    stage="g2d-fifo";error=g2d_hw_fifo_idle(g2d)?0:-EBUSY;
    if(error){detail.reason="fifo-idle";detail.item=0;detail.state=0;detail.value=0;}
    for(job=0;!error && job<G2D_MAX_JOBS;job++){
        u32 state=g2d_hw_get_job_state(g2d,job);
        stage="g2d-job";
        if(state!=G2D_JOB_STATE_DONE){error=-EBUSY;detail.reason="job-state";detail.item=job;detail.state=state;detail.value=0;}
    }
    /* Balance only our enable; retain PM/prepared ownership until reset.
     * An unexpected second gate user cannot be disabled on our behalf. */
    clk_disable(g2d->clock);
    if(!error && __clk_is_enabled(g2d->clock)){stage="g2d-clock-off";error=-EBUSY;detail.reason="clock-enabled";detail.value=1;}
    if(error)goto refused;
    stage="g2d-recheck";
    spin_lock_irqsave(&g2d->lock_task,flags);error=n132_g2d_state_locked(g2d,&detail);
    spin_unlock_irqrestore(&g2d->lock_task,flags);
    if(error)goto refused;
    stage="g2d-record";error=n130_dma_record(device,0);
    if(error){detail.reason="catalog-success";detail.item=0;detail.state=0;detail.value=error;goto refused;}
    goto publish;
refused:
    n131_gate_refused(stage,error,device);
    n132_g2d_detail_log(&detail,device);
    (void)n130_dma_record(device,error);
publish:
    spin_lock_irqsave(&g2d->lock_task,flags);
    g2d->n132_shutdown_result=error;g2d->n132_shutdown_seen=true;
    spin_unlock_irqrestore(&g2d->lock_task,flags);
}

static unsigned int n132_g2d_count;
static int n132_g2d_cached_device(struct device *device,void *unused)
{
    struct g2d_device *g2d;unsigned long flags;int error;struct n132_g2d_detail detail={0};(void)unused;
    if(device->driver!=&g2d_driver.driver)return 0;
    g2d=dev_get_drvdata(device);
    if(!g2d || g2d->dev!=device)return -ENODEV;
    spin_lock_irqsave(&g2d->lock_task,flags);
    error=g2d->n132_shutdown_seen?g2d->n132_shutdown_result:-ENODEV;
    if(!error)error=n132_g2d_state_locked(g2d,&detail);
    spin_unlock_irqrestore(&g2d->lock_task,flags);
    if(!error)error=n131_dma_status(device);
    if(error){if(detail.reason){n131_gate_refused("g2d-recheck",error,device);n132_g2d_detail_log(&detail,device);}return error;}
    n132_g2d_count++;return 0;
}
int n132_g2d_prepare(void)
{
    /* Parent/device shutdown has completed: cached proof only, no PM/MMIO. */
    int error;
    n132_g2d_count=0;
    error=bus_for_each_dev(&platform_bus_type,NULL,NULL,n132_g2d_cached_device);
    if(!error && !n132_g2d_count)error=-ENODEV;
    if(error)n131_gate_refused("g2d-cached",error,NULL);
    return error;
}
