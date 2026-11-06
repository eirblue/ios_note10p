/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in the real native NPU device TU, never a name-based catalog bypass. */
#include <linux/clk-provider.h>
#include <linux/rwsem.h>
#include <linux/v130_kernel_api.h>
#include <linux/note10_legacy_kexec_build.h>
#include <linux/v136_terminal.h>
#if !defined(CONFIG_NOTE10_XNU_KEXEC_HANDOFF) || CONFIG_NOTE10_XNU_KEXEC_HANDOFF != 1 || !defined(CONFIG_EXYNOS_NPU) || !defined(CONFIG_NPU_HARDWARE) || !defined(CONFIG_NPU_INTERFACE) || defined(CONFIG_NPU_LOOPBACK) || defined(CONFIG_NPU_ZEBU_EMULATION) || !defined(CONFIG_SOC_EXYNOS9820) || defined(CONFIG_SOC_EXYNOS9820_EVT0)
#error "NPU proof requires actual Exynos9820 EVT1 hardware/interface profile"
#endif
static DEFINE_SPINLOCK(n136_npu_lock);
static DECLARE_RWSEM(n136_npu_users);
static struct npu_device *n136_npu_owner;
static unsigned int n136_npu_history;
static bool n136_npu_is_ready,n136_npu_frozen,n136_npu_seen;
static int n136_npu_result=-ENODEV;
static struct n136_witness n136_npu_witness;
int n136_npu_register(struct npu_device *device)
{
    unsigned long flags;int error=0;
    spin_lock_irqsave(&n136_npu_lock,flags);
    if(n136_npu_owner || n136_npu_frozen)error=-EBUSY;
    else n136_npu_owner=device;
    spin_unlock_irqrestore(&n136_npu_lock,flags);return error;
}
void n136_npu_ready(struct npu_device *device)
{
    unsigned long flags;spin_lock_irqsave(&n136_npu_lock,flags);
    if(n136_npu_owner==device && !n136_npu_frozen)n136_npu_is_ready=true;
    spin_unlock_irqrestore(&n136_npu_lock,flags);
}
void n136_npu_detach(struct npu_device *device)
{
    unsigned long flags;spin_lock_irqsave(&n136_npu_lock,flags);
    if(device && n136_npu_owner==device){n136_npu_is_ready=false;n136_npu_owner=NULL;n136_npu_history|=N136_DETACH;}
    spin_unlock_irqrestore(&n136_npu_lock,flags);
}
bool n136_npu_event(unsigned int event)
{
    unsigned long flags;bool admit;
    spin_lock_irqsave(&n136_npu_lock,flags);
    admit=n136_npu_owner && n136_npu_is_ready && !n136_npu_frozen;
    /* A real fault notification is evidence even when its dump is refused
     * before ready or after freeze; it cannot disappear from cold history. */
    if(n136_npu_owner && (event&N136_FAULT)){
        n136_npu_history|=N136_FAULT;
        if(n136_npu_seen && !n136_npu_result){
            n136_npu_result=-EIO;
            /* Registry never takes the NPU lock. Publish the invalidation
             * before returning from this same fault admission, no new read. */
            (void)n130_dma_record(n136_npu_owner->dev,-EIO);
        }
    }
    if(admit)n136_npu_history|=event;
    spin_unlock_irqrestore(&n136_npu_lock,flags);return admit;
}
bool n136_npu_user_begin(void)
{
    unsigned long flags;bool admit;
    if(!down_read_trylock(&n136_npu_users))return false;
    spin_lock_irqsave(&n136_npu_lock,flags);
    admit=n136_npu_owner && n136_npu_is_ready && !n136_npu_frozen;
    spin_unlock_irqrestore(&n136_npu_lock,flags);
    if(!admit)up_read(&n136_npu_users);
    return admit;
}
void n136_npu_user_end(void){up_read(&n136_npu_users);}
static void n136_npu_log(const char *stage,int error,struct device *owner,const struct n136_detail *d)
{
    n131_gate_refused(stage,error,owner);
    pr_emerg("N10XNU136 id=%s npu reason=%.24s item=%u state=%u value=%d aux=%u owner=%.64s\n",
        N10_KEXEC_BUILD_ID,d->reason?d->reason:"none",d->item,d->state,d->value,d->aux,dev_name(owner));
}
/* Native vertex and session locks held; no hardware reads in this function. */
static int n136_npu_cold(struct npu_device *d,struct n136_detail *detail)
{
    struct npu_system *s=&d->system;struct npu_memory *m=&s->memory;
    unsigned long flags;unsigned int index,history;bool valid;int error=0;
    spin_lock_irqsave(&n136_npu_lock,flags);
    valid=n136_npu_owner==d && n136_npu_is_ready && n136_npu_frozen;history=n136_npu_history;
    spin_unlock_irqrestore(&n136_npu_lock,flags);
    if(!valid || history){detail->reason="lifetime-history";detail->state=history;return -EBUSY;}
    if(d->state || d->err_state){detail->reason="device-state";detail->state=d->state;detail->aux=d->err_state;return -EBUSY;}
    if(atomic_read(&d->vertex.open_cnt.refcount) || atomic_read(&d->vertex.start_cnt.refcount)){
        detail->reason="vertex-reference";detail->state=atomic_read(&d->vertex.open_cnt.refcount);detail->value=atomic_read(&d->vertex.start_cnt.refcount);return -EBUSY;}
    if(s->resume_steps || s->resume_soc_steps){detail->reason="resume-steps";detail->state=s->resume_steps;detail->aux=s->resume_soc_steps;return -EBUSY;}
    if(atomic_read(&d->sessionmgr.session_cnt)){detail->reason="session-count";detail->value=atomic_read(&d->sessionmgr.session_cnt);return -EBUSY;}
    for(index=0;index<NPU_MAX_SESSION;index++)if(d->sessionmgr.session[index]){
        detail->reason="session-slot";detail->item=index;return -EBUSY;}
    if(m->dev!=d->dev || atomic_read(&m->refcount)){detail->reason="memory-reference";detail->value=atomic_read(&m->refcount);return -EBUSY;}
    spin_lock_irqsave(&m->map_lock,flags);
    if(m->map_count || !list_empty(&m->map_list)){detail->reason="mapped-buffer";detail->state=m->map_count;error=-EBUSY;}
    spin_unlock_irqrestore(&m->map_lock,flags);if(error)return error;
    spin_lock_irqsave(&m->alloc_lock,flags);
    if(m->alloc_count || !list_empty(&m->alloc_list)){detail->reason="allocated-buffer";detail->state=m->alloc_count;error=-EBUSY;}
    spin_unlock_irqrestore(&m->alloc_lock,flags);if(error)return error;
    error=n136_npu_protocol_cold(d,detail);if(error)return error;
    return n136_npu_interface_cold(d,detail);
}
static void n136_npu_shutdown(struct platform_device *pdev)
{
    struct device *owner=&pdev->dev;struct npu_device *d=dev_get_drvdata(owner);
    struct n136_detail detail={"provider",0,0,0,0};unsigned long flags;
    const char *stage="npu-provider";
    bool vertex=false,session=false,cal=false;int error;u32 value;
    if(!n132_handoff_active())return;
    if(!d || d->dev!=owner || d->system.pdev!=pdev){n136_npu_log(stage,-ENODEV,owner,&detail);return;}
    error=n130_dma_record(owner,-EINPROGRESS);
    if(error!=-EINPROGRESS){if(!error)error=-EPERM;detail.reason="catalog-pending";goto refused;}
    stage="npu-users";
    if(!down_write_trylock(&n136_npu_users)){error=-EBUSY;detail.reason="user-access-busy";goto refused;}
    spin_lock_irqsave(&n136_npu_lock,flags);
    if(n136_npu_frozen){error=-EALREADY;detail.reason="duplicate-shutdown";}
    else{n136_npu_frozen=true;error=0;}
    spin_unlock_irqrestore(&n136_npu_lock,flags);up_write(&n136_npu_users);if(error)goto refused;
    stage="npu-lifetime";
    if(!mutex_trylock(&d->vertex.lock)){error=-EBUSY;detail.reason="vertex-lock";goto refused;}vertex=true;
    if(!mutex_trylock(&d->sessionmgr.mlock)){error=-EBUSY;detail.reason="session-lock";goto refused;}session=true;
    error=n136_npu_cold(d,&detail);if(error)goto refused;
    stage="npu-resources";error=-ENODEV;
    if(d->system.pmu_npu.paddr!=0x15861d00 || d->system.pmu_npu.size!=0x100 || !d->system.pmu_npu.vaddr){detail.reason="pmu-resource";goto refused;}
    if(IS_ERR_OR_NULL(d->system.npu_clk)){detail.reason="clock-resource";goto refused;}
    value=__clk_get_enable_count(d->system.npu_clk);
    if(value){error=-EBUSY;detail.reason="clock-reference";detail.state=value;goto refused;}
    stage="npu-cal";error=n136_cal_begin(N136_NPU_DOMAINS,&detail);if(error<0)goto refused;cal=true;
    /* Sole native CAL snapshot has request/status/emulation for both domains.
     * A reserved admission keeps them stable; do not reread or wake firmware. */
    stage="npu-power-off";
    if(error){error=-EBUSY;goto refused;}
    error=n136_npu_cold(d,&detail);if(error)goto refused;
    n136_cal_end(N136_NPU_DOMAINS,true);cal=false;
    error=n136_witness_commit(&n136_npu_witness,owner,N136_NPU_DOMAINS_OFF_FROZEN,N136_NPU_DOMAINS);
    if(!error)error=n130_dma_record(owner,0);
    if(error){detail.reason="typed-catalog";goto refused;}
    goto publish;
refused:
    if(cal)n136_cal_end(N136_NPU_DOMAINS,false);
    n136_npu_log(stage,error,owner,&detail);(void)n130_dma_record(owner,error);
publish:
    spin_lock_irqsave(&n136_npu_lock,flags);n136_npu_seen=true;n136_npu_result=error;
    spin_unlock_irqrestore(&n136_npu_lock,flags);
    if(session)mutex_unlock(&d->sessionmgr.mlock);
    if(vertex)mutex_unlock(&d->vertex.lock);
}
static unsigned int n136_npu_count;
static int n136_npu_cached(struct device *owner,void *unused)
{
    struct npu_device *d=NULL;struct n136_detail detail={0};unsigned long flags;int error;bool vertex=false,session=false;(void)unused;
    if(READ_ONCE(owner->driver)!=&npu_driver.driver)return 0;
    if(!device_trylock(owner))return -EBUSY;
    if(owner->driver!=&npu_driver.driver){error=-ENODEV;goto done;}
    d=dev_get_drvdata(owner);
    if(!d || d->dev!=owner || d->system.pdev==NULL || &d->system.pdev->dev!=owner){error=-ENODEV;goto done;}
    if(!mutex_trylock(&d->vertex.lock)){error=-EBUSY;goto done;}vertex=true;
    if(!mutex_trylock(&d->sessionmgr.mlock)){error=-EBUSY;goto done;}session=true;
    spin_lock_irqsave(&n136_npu_lock,flags);error=n136_npu_seen?n136_npu_result:-ENODEV;
    spin_unlock_irqrestore(&n136_npu_lock,flags);
    if(!error && !n136_witness_valid(&n136_npu_witness,owner,N136_NPU_DOMAINS_OFF_FROZEN,N136_NPU_DOMAINS))error=-EPERM;
    if(!error)error=n136_npu_cold(d,&detail);
    if(!error)error=n131_dma_status(owner);
    if(!error)n136_npu_count++;
done:
    if(session)mutex_unlock(&d->sessionmgr.mlock);
    if(vertex)mutex_unlock(&d->vertex.lock);
    device_unlock(owner);if(error)n136_npu_log("npu-cached",error,owner,&detail);return error;
}
int n136_npu_prepare(void)
{
    int error;n136_npu_count=0;
    error=bus_for_each_dev(&platform_bus_type,NULL,NULL,n136_npu_cached);
    if(!error && n136_npu_count!=1)error=-ENODEV;
    if(error)n131_gate_refused("npu-cached",error,NULL);
    return error;
}
