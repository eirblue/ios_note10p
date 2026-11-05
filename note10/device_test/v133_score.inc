/* SPDX-License-Identifier: GPL-2.0-only */
/* Pinned native SCORE v3/v3_1 lifetime; no SysMMU-state admission. */
#if !defined(CONFIG_NOTE10_XNU_KEXEC_HANDOFF) || CONFIG_NOTE10_XNU_KEXEC_HANDOFF != 1 || !defined(CONFIG_EXYNOS_SCORE_V3) || defined(CONFIG_EXYNOS_SCORE_FPGA) || !defined(SCORE_EVT1)
#error "SCORE proof requires the actual enabled Exynos9820 v3 profile"
#endif
#ifdef N133_SCORE_HARDWARE_TU
/* Native target-halt and DMA-idle predicates, with the already inspected
 * values retained for one bounded refusal record. No reset/cache flush. */
int n133_score_hardware_stop(struct score_system *system,struct n133_score_detail *detail)
{
    unsigned int index,core;u32 cache=0,intr1=0,intr2=0,value=0;
    const unsigned int dma[]={DMA0_QUEUE_STATUS,DMA1_QUEUE_STATUS,DMA2_QUEUE_STATUS,DMA3_QUEUE_STATUS};
    unsigned long flags;int error=0;
    if(system->sfr_size<BR_CACHE_STATUS+sizeof(u32)){detail->reason="mmio-extent";detail->state=system->sfr_size;return -ENODEV;}
    spin_lock_irqsave(&system->cache_slock,flags);
    for(core=0;core<2;core++){
        if(!core)writel(1U<<0,system->sfr+TS_SWI_STATUS);
        else{writel(1U<<0,system->sfr+BR1_SWI_STATUS);writel(1U<<0,system->sfr+BR2_SWI_STATUS);}
        for(index=0;index<CHECK_RETRY_COUNT;index++){
            cache=readl(system->sfr+(core?BR_CACHE_STATUS:TS_CACHE_STATUS));
            intr1=readl(system->sfr+(core?BR1_INTR_ENABLE:TS_INTR_ENABLE));
            intr2=core?readl(system->sfr+BR2_INTR_ENABLE):0;
            if(!(cache|intr1|intr2))break;
            udelay(CHECK_RETRY_DELAY);
        }
        if(cache|intr1|intr2){
            detail->reason=core?"baron-halt":"ts-halt";detail->item=core;
            detail->state=cache;detail->value=(int)intr1;detail->aux=intr2;error=-ETIMEDOUT;goto done;
        }
    }
    for(core=0;core<ARRAY_SIZE(dma);core++){
        for(index=0;index<CHECK_RETRY_COUNT;index++){
            value=readl(system->sfr+dma[core]);
            if(!(value&(1U<<12)))break;
            udelay(CHECK_RETRY_DELAY);
        }
        if(value&(1U<<12)){
            detail->reason="dma-busy";detail->item=core;detail->state=value;
            detail->value=CHECK_RETRY_COUNT;detail->aux=dma[core];error=-ETIMEDOUT;goto done;
        }
    }
done:
    spin_unlock_irqrestore(&system->cache_slock,flags);return error;
}
#else
#include <linux/bitmap.h>
#include <linux/clk-provider.h>
#include <linux/interrupt.h>
#include <linux/timer.h>
#include <linux/v130_kernel_api.h>
#include <linux/note10_legacy_kexec_build.h>
static void n133_score_detail_log(const struct n133_score_detail *detail,struct device *owner)
{
    pr_emerg("N10XNU133 id=%s score reason=%.24s item=%u state=%u value=%d aux=%u owner=%.64s\n",
        N10_KEXEC_BUILD_ID,detail->reason?detail->reason:"none",detail->item,detail->state,detail->value,detail->aux,owner?dev_name(owner):"none");
}
/* Native core.device_lock held. Each subsidiary state uses its own lock;
 * never-opened and permanent admission freeze exclude asynchronous users. */
static int n133_score_state_locked(struct score_device *device,struct n133_score_detail *detail)
{
    struct score_system *system=&device->system;struct score_core *core=&device->core;
    struct score_frame_manager *fm=&system->interface.framemgr;unsigned long flags;int error=0;
    detail->reason=NULL;detail->item=0;detail->state=device->state;detail->value=0;detail->aux=0;
    if(!READ_ONCE(device->n133_user_frozen)){detail->reason="user-admission";return -EBUSY;}
    if(!device->n133_terminal){detail->reason="not-terminal";return -EBUSY;}
    if(device->n133_ever_opened){detail->reason="open-history";return -EBUSY;}
    if(atomic_read(&device->open_count)){detail->reason="open-count";return -EBUSY;}
    if(device->state!=BIT(SCORE_DEVICE_STATE_CLOSE)){detail->reason="device-state";return -EBUSY;}
    spin_lock_irqsave(&system->n133_boot_lock,flags);
    if(!system->n133_terminal || system->n133_ever_booted){detail->reason="boot-history";detail->value=system->n133_ever_booted;error=-EBUSY;}
    spin_unlock_irqrestore(&system->n133_boot_lock,flags);if(error)return error;
    spin_lock_irqsave(&core->ctx_slock,flags);
    if(core->ctx_count || !list_empty(&core->ctx_list)){detail->reason="contexts";detail->value=core->ctx_count;error=-EBUSY;}
    spin_unlock_irqrestore(&core->ctx_slock,flags);if(error)return error;
    spin_lock_irqsave(&fm->slock,flags);
    if(!fm->block){detail->reason="frame-admission";error=-EBUSY;}
    else{
        unsigned int index;const u32 counts[]={fm->all_count,fm->normal_count,fm->abnormal_count,
            fm->entire_count,fm->ready_count,fm->process_count,fm->pending_count,fm->complete_count,
            fm->process_high_count,fm->process_normal_count,fm->pending_high_count,fm->pending_normal_count};
        for(index=0;index<ARRAY_SIZE(counts);index++)if(counts[index]){
            detail->reason=index<3?"frame-history":"frame-count";detail->item=index;
            detail->state=counts[index];error=-EBUSY;break;
        }
        if(!error && (!list_empty(&fm->entire_list) || !list_empty(&fm->ready_list) || !list_empty(&fm->process_list) ||
            !list_empty(&fm->pending_list) || !list_empty(&fm->complete_list) || !bitmap_empty(fm->frame_map,SCORE_MAX_FRAME))){detail->reason="frame-list";error=-EBUSY;}
    }
    spin_unlock_irqrestore(&fm->slock,flags);if(error)return error;
    spin_lock_irqsave(&system->mmu.free_slock,flags);
    if(system->mmu.free_count || !list_empty(&system->mmu.free_list)){detail->reason="mmu-free";detail->value=system->mmu.free_count;error=-EBUSY;}
    spin_unlock_irqrestore(&system->mmu.free_slock,flags);if(error)return error;
    if(system->scq.state!=BIT(SCORE_SCQ_STATE_CLOSE) || system->scq.count || system->scq.high_count || system->scq.normal_count){detail->reason="scq-state";detail->state=system->scq.state;return -EBUSY;}
    if(system->print.init || timer_pending(&system->print.timer)){detail->reason="print-timer";detail->state=system->print.init;return -EBUSY;}
    return 0;
}

static void n133_score_shutdown(struct platform_device *pdev)
{
    struct device *owner=&pdev->dev;struct score_device *device=dev_get_drvdata(owner);
    struct score_system *system;unsigned long flags;int error;bool locked=false;
    const char *stage="score-provider";struct n133_score_detail detail={"provider",0,0,0,0};
    if(!device || device->dev!=owner || device->pdev!=pdev){n131_gate_refused(stage,-ENODEV,owner);n133_score_detail_log(&detail,owner);return;}
    system=&device->system;stage="score-record";error=n130_dma_record(owner,-EINPROGRESS);
    if(error!=-EINPROGRESS){if(!error)error=-EPERM;detail.reason="catalog-pending";detail.value=error;goto refused;}
    stage="score-users";
    /* Native sysfs/profiler callbacks may take core/PM/cache locks. Never
     * wait on a holder while device_shutdown owns the device mutex. */
    if(!down_write_trylock(&device->n133_user_lock)){error=-EBUSY;detail.reason="user-access-busy";goto refused;}
    device->n133_user_frozen=true;up_write(&device->n133_user_lock);
    stage="score-lifetime";
    if(!mutex_trylock(&device->core.device_lock)){error=-EBUSY;detail.reason="device-lock";goto refused;}
    locked=true;
    if(device->n133_terminal){error=-EALREADY;detail.reason="duplicate-shutdown";goto refused;}
    device->n133_terminal=true;
    spin_lock_irqsave(&system->n133_boot_lock,flags);system->n133_terminal=true;
    spin_unlock_irqrestore(&system->n133_boot_lock,flags);
    spin_lock_irqsave(&system->interface.framemgr.slock,flags);
    score_frame_manager_block(&system->interface.framemgr);
    spin_unlock_irqrestore(&system->interface.framemgr.slock,flags);
    error=n133_score_state_locked(device,&detail);if(error)goto refused;
    stage="score-resources";error=-ENODEV;detail.state=0;
    if(system->dev!=owner || !system->sfr){detail.reason="mmio-resource";goto refused;}
    if(system->interface.dev!=owner || system->interface.irq0<=0){detail.reason="irq-resource";goto refused;}
    if(IS_ERR_OR_NULL(device->clk.clkm) || IS_ERR_OR_NULL(device->clk.clks)){detail.reason="clock-resource";goto refused;}
    if(IS_ERR_OR_NULL(system->scq.write_task) || IS_ERR_OR_NULL(system->mmu.unmap_task)){detail.reason="worker-resource";goto refused;}
    disable_irq_nosync(system->interface.irq0);synchronize_irq(system->interface.irq0);
    kthread_flush_worker(&system->scq.write_worker);kthread_flush_worker(&system->mmu.unmap_worker);
    error=n133_score_state_locked(device,&detail);if(error)goto refused;
    stage="score-power";
    if(!pm_runtime_enabled(owner) || !pm_runtime_suspended(owner)){error=-EBUSY;detail.reason="pm-not-suspended";goto refused;}
    if(__clk_is_enabled(device->clk.clkm) || __clk_is_enabled(device->clk.clks)){error=-EBUSY;detail.reason="initial-clock-user";goto refused;}
#ifdef CONFIG_PM_DEVFREQ
    error=score_pm_qos_set_default(&device->pm,device->pm.qos_count-1);
    if(error){detail.reason="pm-default";detail.value=error;goto refused;}
#endif
    error=pm_runtime_get_sync(owner);
    if(error<0){pm_runtime_put_noidle(owner);detail.reason="pm-get";detail.value=error;goto refused;}
    if(error>0){pm_runtime_put_noidle(owner);detail.reason="pm-already-active";detail.value=error;error=-EBUSY;goto refused;}
    if(pm_runtime_suspended(owner)){error=-EIO;detail.reason="pm-still-suspended";goto refused;}
    /* Real native resume enables exactly these two gates and cannot boot or
     * submit DSP work. Its successful owned reference remains held. */
    stage="score-halt";error=n133_score_hardware_stop(system,&detail);
    /* Native device_shutdown retains an extra noresume reference. Stop PM
     * callbacks and balance only our successful native-resume gate enables;
     * preserve preparation, PM and QoS ownership until reset/transfer. */
    pm_runtime_disable(owner);
    clk_disable(device->clk.clks);clk_disable(device->clk.clkm);
    if(error)goto refused;
    stage="score-clock-off";
    if(__clk_is_enabled(device->clk.clkm)){error=-EBUSY;detail.reason="dspm-clock-user";detail.item=0;detail.state=1;goto refused;}
    if(__clk_is_enabled(device->clk.clks)){error=-EBUSY;detail.reason="dsps-clock-user";detail.item=1;detail.state=1;goto refused;}
    stage="score-recheck";error=n133_score_state_locked(device,&detail);if(error)goto refused;
    stage="score-record";error=n130_dma_record(owner,0);
    if(error){detail.reason="catalog-success";detail.value=error;goto refused;}
    goto publish;
refused:
    n131_gate_refused(stage,error,owner);n133_score_detail_log(&detail,owner);
    (void)n130_dma_record(owner,error);
publish:
    /* Cache even an admission-lock refusal without waiting for that lock. */
    spin_lock_irqsave(&system->n133_boot_lock,flags);
    device->n133_shutdown_result=error;device->n133_shutdown_seen=true;
    spin_unlock_irqrestore(&system->n133_boot_lock,flags);
    if(locked)mutex_unlock(&device->core.device_lock);
}

static unsigned int n133_score_count;
static int n133_score_cached_device(struct device *owner,void *unused)
{
    struct score_device *device;unsigned long flags;int error;struct n133_score_detail detail={0};(void)unused;
    if(READ_ONCE(owner->driver)!=&score_driver.driver)return 0;
    /* bus iteration pins owner; native device mutex excludes driver remove
     * while the real driver data and its core lock are being consumed. */
    if(!device_trylock(owner))return -EBUSY;
    if(owner->driver!=&score_driver.driver){device_unlock(owner);return -ENODEV;}
    device=dev_get_drvdata(owner);
    if(!device || device->dev!=owner || !device->pdev || &device->pdev->dev!=owner){device_unlock(owner);return -ENODEV;}
    if(!mutex_trylock(&device->core.device_lock)){device_unlock(owner);return -EBUSY;}
    spin_lock_irqsave(&device->system.n133_boot_lock,flags);
    error=device->n133_shutdown_seen?device->n133_shutdown_result:-ENODEV;
    spin_unlock_irqrestore(&device->system.n133_boot_lock,flags);
    if(!error)error=n133_score_state_locked(device,&detail);
    mutex_unlock(&device->core.device_lock);
    if(!error)error=n131_dma_status(owner);
    device_unlock(owner);
    if(error){if(detail.reason){n131_gate_refused("score-recheck",error,owner);n133_score_detail_log(&detail,owner);}return error;}
    n133_score_count++;return 0;
}
int n133_score_prepare(void)
{
    int error;n133_score_count=0;
    /* Parents have shut down: exact cached lifetime/catalog only. */
    error=bus_for_each_dev(&platform_bus_type,NULL,NULL,n133_score_cached_device);
    if(!error && !n133_score_count)error=-ENODEV;
    if(error)n131_gate_refused("score-cached",error,NULL);
    return error;
}
#endif
