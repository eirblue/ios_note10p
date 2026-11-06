/* SPDX-License-Identifier: GPL-2.0-only */
/* Included at the end of the selected native TU, after its static driver. */
#include <linux/err.h>
#include <linux/of_address.h>
#include <linux/platform_device.h>
#include <linux/workqueue.h>
#include <linux/v138_display.h>
static bool __maybe_unused n138_resource(struct n138_slot *slot,unsigned int index,
                                        resource_size_t start,resource_size_t size)
{
    struct resource *res=platform_get_resource(to_platform_device(slot->dev),IORESOURCE_MEM,index);
    return res && res->start==start && resource_size(res)==size;
}
static int __maybe_unused n138_native_bad(struct n136_detail *detail,const char *reason,
                                         unsigned int id,int error)
{
    detail->reason=reason;detail->item=id;detail->value=error;return error;
}
static bool __maybe_unused n138_irq_resource(struct n138_slot *slot,unsigned int index,int irq)
{
    struct resource *res=platform_get_resource(to_platform_device(slot->dev),IORESOURCE_IRQ,index);
    return irq>0 && res && res->start==res->end && res->start==(resource_size_t)irq;
}

#ifdef N138_DECON_NATIVE
static int n138_decon_validate(struct n138_slot *slot,struct n136_detail *detail)
{
    struct decon_device *decon=slot->object;unsigned long mask;unsigned int id;
    if((slot->id!=0 && slot->id!=2) || decon_drvdata[slot->id]!=decon ||
       decon->id!=(int)slot->id || decon->dev!=slot->dev ||
       !n138_resource(slot,0,slot->id?0x19050000:0x19030000,0x10000) ||
       IS_ERR_OR_NULL(decon->res.regs) || IS_ERR_OR_NULL(decon->res.ss_regs) ||
       decon->dt.out_type!=(slot->id?DECON_OUT_DP:DECON_OUT_DSI))
        return n138_native_bad(detail,"decon-resource",slot->id,-ENODEV);
    if(decon->dt.out_idx[0]!=0 || decon->dt.dsi_mode!=DSI_MODE_SINGLE ||
       decon->dt.trig_mode!=DECON_HW_TRIG ||
       decon->dt.psr_mode!=(slot->id?DECON_VIDEO_MODE:DECON_MIPI_COMMAND_MODE))
        return n138_native_bad(detail,"decon-selected-mode",slot->id,-ENODEV);
    for(id=0;id<3;id++){
        struct resource *res=platform_get_resource(to_platform_device(slot->dev),IORESOURCE_IRQ,id);
        if(!res || !res->start || res->start!=res->end)return n138_native_bad(detail,"decon-irq-resource",id,-ENODEV);
    }
    if(decon->dt.out_type==DECON_OUT_DSI && decon->dt.psr_mode!=DECON_VIDEO_MODE){
        /* GPIO TE virq has no platform IRQ resource. Capture its sole native
         * gpio_to_irq assignment only during resource-qualified probe. */
        if(decon->res.irq<=0)return n138_native_bad(detail,"decon-te-resource",slot->id,-ENODEV);
        if(slot->lifetime==N138_PROBING)slot->native_irq=decon->res.irq;
        else if(slot->native_irq!=decon->res.irq)return n138_native_bad(detail,"decon-te-generation",slot->id,-ENODEV);
    }
    if(decon->state==DECON_STATE_TUI || decon->prev_protection_bitmask)
        return n138_native_bad(detail,"secure-history",slot->id,-EPERM);
    mask=decon->prev_used_dpp|decon->cur_using_dpp|decon->dpp_err_stat;
    if(mask&~0x3fUL)return n138_native_bad(detail,"unknown-channel",slot->id,-ENODEV);
    for(id=0;id<6;id++)if((mask&(1UL<<id)) && !n138_lease_matches(id,decon))
        return n138_native_bad(detail,"peer-lease",id,-EPERM);
    return 0;
}
static int n138_decon_lock(struct n138_slot *slot,struct n136_detail *detail)
{
    struct decon_device *decon=slot->object;
    if(!mutex_trylock(&decon->pwr_state_lock))goto busy;
    if(!mutex_trylock(&decon->lock))goto power;
    if(!mutex_trylock(&decon->pm_lock))goto main;
    if(!mutex_trylock(&decon->cursor.lock))goto pm;
    if(!mutex_trylock(&decon->up.lock))goto cursor;
    if(decon->hiber.enabled && !mutex_trylock(&decon->hiber.lock))goto update;
#ifdef CONFIG_EXYNOS_COMMON_PANEL
    if(decon->doze_hiber.enabled && !mutex_trylock(&decon->doze_hiber.lock))goto hiber;
#endif
    return 0;
#ifdef CONFIG_EXYNOS_COMMON_PANEL
hiber:
    if(decon->hiber.enabled)mutex_unlock(&decon->hiber.lock);
#endif
update:mutex_unlock(&decon->up.lock);
cursor:mutex_unlock(&decon->cursor.lock);
pm:mutex_unlock(&decon->pm_lock);
main:mutex_unlock(&decon->lock);
power:mutex_unlock(&decon->pwr_state_lock);
busy:return n138_native_bad(detail,"decon-lock",slot->id,-EBUSY);
}
static void n138_decon_unlock(struct n138_slot *slot)
{
    struct decon_device *decon=slot->object;
#ifdef CONFIG_EXYNOS_COMMON_PANEL
    if(decon->doze_hiber.enabled)mutex_unlock(&decon->doze_hiber.lock);
#endif
    if(decon->hiber.enabled)mutex_unlock(&decon->hiber.lock);
    mutex_unlock(&decon->up.lock);mutex_unlock(&decon->cursor.lock);
    mutex_unlock(&decon->pm_lock);mutex_unlock(&decon->lock);
    mutex_unlock(&decon->pwr_state_lock);
}
static int n138_worker_quiet(struct kthread_worker *worker)
{
    unsigned long flags;bool quiet;
    if(!spin_trylock_irqsave(&worker->lock,flags))return -EBUSY;
    quiet=!worker->current_work && list_empty(&worker->work_list) &&
        list_empty(&worker->delayed_work_list);
    spin_unlock_irqrestore(&worker->lock,flags);return quiet?0:-EBUSY;
}
static int n138_decon_quiet(struct n138_slot *slot,struct n136_detail *detail)
{
    struct decon_device *decon=slot->object;struct resource *res;unsigned int index;
    if(!decon->up.thread || decon->up_list_saved ||
       atomic_read(&decon->up.remaining_frame) || !list_empty(&decon->up.list) ||
       n138_worker_quiet(&decon->up.worker))
        return n138_native_bad(detail,"decon-update-work",slot->id,-EBUSY);
#ifndef CONFIG_EXYNOS_HIBERNATION_THREAD
    if(decon->hiber.enabled && (atomic_read(&decon->hiber.remaining_hiber) ||
       n138_worker_quiet(&decon->hiber.worker)))
        return n138_native_bad(detail,"decon-hiber-work",slot->id,-EBUSY);
#endif
    /* Native handlers are exclusive (request_irq flags have no SHARED).
     * Atomic entry closure proves no native callback remains in progress;
     * nosync acquires only our disable level, without a drain wait. */
    for(index=0;index<3;index++){
        res=platform_get_resource(to_platform_device(slot->dev),IORESOURCE_IRQ,index);
        if(!res || !res->start)return n138_native_bad(detail,"decon-irq",index,-ENODEV);
        disable_irq_nosync(res->start);
    }
    if(decon->dt.out_type==DECON_OUT_DSI && decon->dt.psr_mode!=DECON_VIDEO_MODE){
        if(decon->res.irq<=0)return n138_native_bad(detail,"decon-te-irq",slot->id,-ENODEV);
        disable_irq_nosync(decon->res.irq);
    }
    return 0;
}
static int n138_decon_stop(struct n138_slot *slot,struct n136_detail *detail)
{
    struct decon_device *decon=slot->object;struct decon_mode_info psr;unsigned int fps=0;
    (void)detail;
    decon_to_psr_info(decon,&psr);
    if(decon->lcd_info)fps=decon->lcd_info->fps;
    return n138_native_decon_stop(slot->id,&psr,fps);
}
const struct n138_native_ops *n138_decon_native(void)
{
    static const struct n138_native_ops ops={
        "samsung,exynos9-decon","decon",N138_DECON,3,&decon_driver.driver,
        n138_decon_validate,n138_decon_lock,n138_decon_unlock,n138_decon_quiet,n138_decon_stop};
    return &ops;
}
#endif

#ifdef N138_DPP_NATIVE
static int n138_dpp_validate(struct n138_slot *slot,struct n136_detail *detail)
{
    static const u32 dma[]={0x19071000,0x19076000,0x19072000,0x19075000,0x19073000,0x19074000};
    static const u32 dppbase[]={0x19021000,0x19026000,0x19022000,0x19024000,0x19023000,0x19025000};
    static const unsigned long attrs[]={0x50007,0x5007f,0x50007,0x50017,0x50016,0x50036};
    static const unsigned int ports[]={0,0,1,1,2,2};
    struct dpp_device *dpp=slot->object;u32 native_attr,native_port;
    if(slot->id>=6 || dpp_drvdata[slot->id]!=dpp || dpp->id!=(int)slot->id ||
       dpp->dev!=slot->dev || !n138_resource(slot,0,dma[slot->id],0x1000) ||
       !n138_resource(slot,1,dppbase[slot->id],0x1000) ||
       IS_ERR_OR_NULL(dpp->res.dma_regs) || IS_ERR_OR_NULL(dpp->res.regs) ||
       !n138_irq_resource(slot,0,dpp->res.dma_irq) || !n138_irq_resource(slot,1,dpp->res.irq) ||
       of_property_read_u32(slot->dev->of_node,"attr",&native_attr) ||
       of_property_read_u32(slot->dev->of_node,"port",&native_port) ||
       native_attr!=attrs[slot->id] || native_port!=ports[slot->id] ||
       dpp->port!=(int)native_port || (dpp->attr&~0x380UL)!=native_attr)
        return n138_native_bad(detail,"dpp-resource",slot->id,-ENODEV);
    if(!slot->id && (!n138_resource(slot,2,0x19070000,0x110) || IS_ERR_OR_NULL(dpp->res.dma_com_regs)))
        return n138_native_bad(detail,"dpp-common-resource",slot->id,-ENODEV);
    /* UNBORROWED is programming ownership, never an idle observation. A
     * borrowed lease can only name a completed native peer after freeze. */
    return 0;
}
static int n138_dpp_lock(struct n138_slot *slot,struct n136_detail *detail)
{
    struct dpp_device *dpp=slot->object;
    return mutex_trylock(&dpp->lock)?0:n138_native_bad(detail,"dpp-lock",slot->id,-EBUSY);
}
static void n138_dpp_unlock(struct n138_slot *slot)
{ struct dpp_device *dpp=slot->object;mutex_unlock(&dpp->lock); }
static int n138_dpp_quiet(struct n138_slot *slot,struct n136_detail *detail)
{
    struct dpp_device *dpp=slot->object;
    del_timer(&dpp->d.op_timer);
    if(timer_pending(&dpp->d.op_timer))return n138_native_bad(detail,"dpp-timer",slot->id,-EBUSY);
    disable_irq_nosync(dpp->res.dma_irq);disable_irq_nosync(dpp->res.irq);
    return 0;
}
static int n138_dpp_stop(struct n138_slot *slot,struct n136_detail *detail)
{
    struct dpp_device *dpp=slot->object;int error;
    (void)detail;
    error=n138_native_dpp_stop(slot->id,dpp->attr);
    if(error)return error;
    error=n138_checkpoint();if(error)return error;
    /* Neither old stateOFF nor a local mask authorizes this assignment. */
    dpp->state=DPP_STATE_OFF;return 0;
}
int n138_owned_config(struct decon_device *decon,struct v4l2_subdev *sd,const struct dpp_config *config)
{
    struct dpp_device *dpp;struct n138_config_guard guard;int error;
    if(!config){n138_invalid();return -EINVAL;}
    error=n138_config_begin(decon,sd,&guard);if(error)return error;
    dpp=guard.channel->object;
    if(!dpp || dpp->id<0 || dpp->id>=6 || dpp_drvdata[dpp->id]!=dpp || &dpp->sd!=sd){
        n138_invalid();error=-ENODEV;goto done;}
    mutex_lock(&dpp->lock);
    if(!n138_borrow(dpp->id,decon) || !n138_dpp_transaction_begin(dpp->id)){
        error=-EPERM;goto unlock;}
    dpp->n138_saved_config=*config;dpp->dpp_config=&dpp->n138_saved_config;
    error=dpp_set_config(dpp);
    n138_dpp_transaction_end(dpp->id);
unlock:mutex_unlock(&dpp->lock);
done:n138_config_end(&guard);return error;
}
const struct n138_native_ops *n138_dpp_native(void)
{
    static const struct n138_native_ops ops={
        "samsung,exynos9-dpp","dpp",N138_DPP,6,&dpp_driver.driver,
        n138_dpp_validate,n138_dpp_lock,n138_dpp_unlock,n138_dpp_quiet,n138_dpp_stop};
    return &ops;
}
#endif

#ifdef N138_DP_NATIVE
bool n138_native_dp_link_ready(void *object)
{
    struct displayport_device *dp=object;
    return dp && displayport_drvdata==dp && dp->state==DISPLAYPORT_STATE_ON;
}
static int n138_dp_validate(struct n138_slot *slot,struct n136_detail *detail)
{
    struct displayport_device *dp=slot->object;
    if(slot->id || displayport_drvdata!=dp || dp->dev!=slot->dev ||
       !n138_resource(slot,0,0x130b0000,0xffff) || !n138_resource(slot,1,0x10ae0000,0x20cc) ||
       IS_ERR_OR_NULL(dp->res.link_regs) || IS_ERR_OR_NULL(dp->res.phy_regs) ||
       !n138_irq_resource(slot,0,dp->res.irq) || !dp->dp_wq || !dp->hdcp2_wq)
        return n138_native_bad(detail,"dp-resource",slot->id,-ENODEV);
    return 0;
}
static int n138_dp_lock(struct n138_slot *slot,struct n136_detail *detail)
{
    struct displayport_device *dp=slot->object;
    if(!mutex_trylock(&dp->hpd_lock))goto busy;
    if(!mutex_trylock(&dp->training_lock))goto hpd;
    if(!mutex_trylock(&dp->cmd_lock))goto training;
    if(!mutex_trylock(&dp->aux_lock))goto command;
    if(!mutex_trylock(&dp->hdcp2_lock))goto aux;
    return 0;
aux:mutex_unlock(&dp->aux_lock);
command:mutex_unlock(&dp->cmd_lock);
training:mutex_unlock(&dp->training_lock);
hpd:mutex_unlock(&dp->hpd_lock);
busy:return n138_native_bad(detail,"dp-lock",slot->id,-EBUSY);
}
static void n138_dp_unlock(struct n138_slot *slot)
{
    struct displayport_device *dp=slot->object;
    mutex_unlock(&dp->hdcp2_lock);mutex_unlock(&dp->aux_lock);
    mutex_unlock(&dp->cmd_lock);mutex_unlock(&dp->training_lock);mutex_unlock(&dp->hpd_lock);
}
static int n138_cancel(struct delayed_work *work)
{ cancel_delayed_work(work);return work_busy(&work->work)?-EBUSY:0; }
static int n138_dp_quiet(struct n138_slot *slot,struct n136_detail *detail)
{
    struct displayport_device *dp=slot->object;
    if(n138_cancel(&dp->hpd_plug_work) || n138_cancel(&dp->hpd_unplug_work) ||
       n138_cancel(&dp->hpd_irq_work) || n138_cancel(&dp->hdcp13_work) ||
       n138_cancel(&dp->hdcp22_work) || n138_cancel(&dp->hdcp13_integrity_check_work))
        return n138_native_bad(detail,"dp-delayed-work",slot->id,-EBUSY);
#ifdef CONFIG_USB_TYPEC_MANAGER_NOTIFIER
    if(n138_cancel(&dp->notifier_register_work))
        return n138_native_bad(detail,"dp-notifier-work",slot->id,-EBUSY);
#endif
    disable_irq_nosync(dp->res.irq);return 0;
}
const struct n138_native_ops *n138_dp_native(void)
{
    static const struct n138_native_ops ops={
        "samsung,exynos-displayport",NULL,N138_DP,1,&displayport_driver.driver,
        n138_dp_validate,n138_dp_lock,n138_dp_unlock,n138_dp_quiet,NULL};
    return &ops;
}
#endif

#ifdef N138_DSIM_NATIVE
bool n138_native_dsim_link_ready(void *object)
{
    struct dsim_device *dsim=object;
    return dsim && dsim->id==0 && dsim_drvdata[0]==dsim && dsim->state==DSIM_STATE_ON;
}
static int n138_dsim_validate(struct n138_slot *slot,struct n136_detail *detail)
{
    struct dsim_device *dsim=slot->object;
    if(slot->id || dsim_drvdata[slot->id]!=dsim || dsim->id!=(int)slot->id || dsim->dev!=slot->dev ||
       !n138_resource(slot,0,0x19080000,0x300) || !n138_resource(slot,1,0x19161000,0x800) ||
       !n138_resource(slot,2,0x19160000,0x100) || IS_ERR_OR_NULL(dsim->res.regs) ||
       IS_ERR_OR_NULL(dsim->res.phy_regs) || IS_ERR_OR_NULL(dsim->res.phy_regs_ex) ||
       !n138_irq_resource(slot,0,dsim->res.irq) || !dsim->wq)
        return n138_native_bad(detail,"dsim-resource",slot->id,-ENODEV);
    return 0;
}
static int n138_dsim_lock(struct n138_slot *slot,struct n136_detail *detail)
{
    struct dsim_device *dsim=slot->object;
    return mutex_trylock(&dsim->cmd_lock)?0:n138_native_bad(detail,"dsim-lock",slot->id,-EBUSY);
}
static void n138_dsim_unlock(struct n138_slot *slot)
{ struct dsim_device *dsim=slot->object;mutex_unlock(&dsim->cmd_lock); }
static int n138_dsim_quiet(struct n138_slot *slot,struct n136_detail *detail)
{
    struct dsim_device *dsim=slot->object;
    del_timer(&dsim->cmd_timer);cancel_work(&dsim->wr_timeout_work);
    if(timer_pending(&dsim->cmd_timer) || work_busy(&dsim->wr_timeout_work))
        return n138_native_bad(detail,"dsim-command-work",slot->id,-EBUSY);
    disable_irq_nosync(dsim->res.irq);return 0;
}
const struct n138_native_ops *n138_dsim_native(void)
{
    static const struct n138_native_ops ops={
        "samsung,exynos9-dsim","dsim",N138_DSIM,2,&dsim_driver.driver,
        n138_dsim_validate,n138_dsim_lock,n138_dsim_unlock,n138_dsim_quiet,NULL};
    return &ops;
}
#endif

#ifdef N138_DECON_CAL
int n138_native_decon_stop(unsigned int id,struct decon_mode_info *psr,unsigned int fps)
{
    int error;u32 running;
    if(!n138_proving())return n138_refuse_access("proof-context",id,0);
    error=n138_checkpoint();if(error)return error;
    running=decon_reg_get_run_status(id);
    error=n138_checkpoint();if(error)return error;
    if(!running)return 0;
    if(!psr || !fps || fps>1000 ||
       (psr->out_type!=DECON_OUT_DSI && psr->out_type!=DECON_OUT_DP))
        return n138_poll_failure("decon-mode",id,running,-EINVAL);
    if(psr->out_type==DECON_OUT_DP && !n138_dp_accessible())
        return n138_poll_failure("dp-access-lease",id,running,-EHOSTDOWN);
#if !defined(CONFIG_SOC_EXYNOS9820_EVT0) && defined(CONFIG_EXYNOS_PLL_SLEEP)
    if(psr->psr_mode==DECON_MIPI_COMMAND_MODE && psr->dsi_mode!=DSI_MODE_DUAL_DSI){
        decon_reg_set_pll_wakeup(id,1);
        error=n138_checkpoint();if(error)return error;
    }
#endif
    if(psr->out_type==DECON_OUT_DP){
        error=n138_shared_te_begin();if(error)return error;
        decon_reg_set_te_qactive_pll_mode(id,0);
        n138_shared_te_end();error=n138_checkpoint();if(error)return error;
    }
    decon_reg_set_int(id,psr,0);
    error=n138_checkpoint();if(error)return error;
    error=decon_reg_stop_perframe(id,0,psr,fps);
    if(error){
        int checkpoint=n138_checkpoint();if(checkpoint)return checkpoint;
        error=decon_reg_stop_inst(id,0,psr,fps);
        if(!error)n138_resolved_failure();
    }
    if(error)return error;
    error=n138_checkpoint();if(error)return error;
    /* Native stop(...,rst=true) also resets this owned controller, but
     * discarded reset errors. Preserve its actual ACK and first errno. */
    error=decon_reg_reset(id);if(error)return error;
    error=n138_checkpoint();if(error)return error;
    decon_reg_clear_int_all(id);return n138_checkpoint();
}
#endif

#ifdef N138_DPP_CAL
int n138_native_dpp_stop(unsigned int id,unsigned long attr)
{
    int error;
    if(!n138_proving())return n138_refuse_access("proof-context",id,0);
    error=n138_checkpoint();
    if(error)return error;
    if(id>=6 || !test_bit(DPP_ATTR_IDMA,&attr) || !test_bit(DPP_ATTR_DPP,&attr) ||
       test_bit(DPP_ATTR_ODMA,&attr))return n138_poll_failure("dpp-variant",id,attr,-ENODEV);
    /* Exact selected native deinit reset sequence; never DMA_COM/global reset.
     * Its wait helpers now propagate the shared deadline/access fault. */
    error=dpp_reg_deinit(id,true,attr);
    if(error)return error;
    return n138_checkpoint();
}
#endif
