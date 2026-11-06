/* SPDX-License-Identifier: GPL-2.0-only */
/* Aggregate native DPU programming ownership, not physical clock state. */
#include <linux/device.h>
#include <linux/interrupt.h>
#include <linux/ktime.h>
#include <linux/of.h>
#include <linux/pm_runtime.h>
#include <linux/sched.h>
#include <linux/spinlock.h>
#include <linux/string.h>
#include <linux/v130_kernel_api.h>
#include <linux/v138_display.h>
#include <linux/note10_legacy_kexec_build.h>
#if !defined(CONFIG_NOTE10_XNU_KEXEC_HANDOFF) || CONFIG_NOTE10_XNU_KEXEC_HANDOFF != 1 || !defined(CONFIG_SOC_EXYNOS9820) || defined(CONFIG_SOC_EXYNOS9820_EVT0) || !defined(CONFIG_EXYNOS_DPU20) || !defined(CONFIG_EXYNOS_DPP) || !defined(CONFIG_EXYNOS_DISPLAYPORT)
#error "v138 requires the selected native Exynos9820 EVT1 DPU20 profile"
#endif
#if !defined(CONFIG_EXYNOS_MIPI_DSIM) || !defined(CONFIG_SAMSUNG_TUI) || !defined(CONFIG_EXYNOS_CONTENT_PATH_PROTECTION) || !defined(CONFIG_EXYNOS_MCD_HDR) || !defined(CONFIG_EXYNOS_HDCP2) || !defined(CONFIG_EXYNOS_COMMON_PANEL) || !defined(CONFIG_EXYNOS_PLL_SLEEP) || !defined(CONFIG_USB_TYPEC_MANAGER_NOTIFIER) || !defined(CONFIG_EXTCON) || !defined(CONFIG_TYPEC) || !defined(CONFIG_EXYNOS_HIBERNATION_THREAD) || !defined(CONFIG_PM) || defined(CONFIG_SUPPORT_LEGACY_FENCE)
#error "v138 requires the exact accepted137 shared-display closure branches"
#endif
#define N138_SLOTS 12
#define N138_POLL_LIMIT 25000U
#define N138_BUDGET_NS 250000000LL
static DEFINE_SPINLOCK(n138_lock);
static struct n138_slot n138_slots[N138_SLOTS];
static struct task_struct *n138_dpp_writer[6];
struct n138_context { struct task_struct *task; unsigned int depth; bool interrupt; };
static struct n138_context n138_contexts[64];
static unsigned int n138_active, n138_history;
static bool n138_closed, n138_seen, n138_complete, n138_cal_reserved;
static bool n138_aborting;
static bool n138_final_seen;
static int n138_final_result=-ENODEV;
static struct task_struct *n138_core_owner;
static int n138_result=-ENODEV;
static int n138_fault_errno;
static struct task_struct *n138_proof_task;
static int n138_selected_family=-1, n138_selected_id=-1;
static bool n138_link_access;
static bool n138_shared_te;
static unsigned int n138_polls;
static s64 n138_deadline;
static struct n136_detail n138_detail;
static struct n136_witness n138_witness;
static const unsigned int n138_offsets[]={0,3,9,10};
static const unsigned int n138_counts[]={3,6,1,2};

static struct n138_slot *n138_find(unsigned int family,unsigned int id)
{
    if(family>=ARRAY_SIZE(n138_counts) || id>=n138_counts[family])return NULL;
    return &n138_slots[n138_offsets[family]+id];
}
static bool n138_is_proof(void)
{ return n138_proof_task==current && !in_interrupt(); }
static struct n138_context *n138_context_locked(void)
{
    unsigned int i;bool interrupt=in_interrupt();
    for(i=0;i<ARRAY_SIZE(n138_contexts);i++)if(n138_contexts[i].depth &&
        n138_contexts[i].task==current && n138_contexts[i].interrupt==interrupt)
        return &n138_contexts[i];
    return NULL;
}
static bool n138_open_locked(void)
{
    /* If an admitted-before call exists, this handoff has already refused
     * before any controller action. Let only that execution finish nested
     * native calls, rather than injecting fake reads into an active handler.
     * This path can never produce a successful terminal witness. */
    return !n138_closed || (n138_aborting && n138_context_locked());
}
static bool n138_ticket_locked(void)
{
    struct n138_context *context=n138_context_locked();unsigned int i;
    if(!context)for(i=0;i<ARRAY_SIZE(n138_contexts);i++)if(!n138_contexts[i].depth){
        context=&n138_contexts[i];context->task=current;context->interrupt=in_interrupt();break;
    }
    if(!context || context->depth==~0U || n138_active==~0U){n138_history|=1;return false;}
    context->depth++;n138_active++;return true;
}
static bool n138_proof_budget_locked(void)
{
    if(n138_history)return false;
    if(!n138_polls || ktime_get_ns()>=n138_deadline){
        n138_history|=64;n138_fault_errno=-ETIMEDOUT;
        if(!n138_detail.reason){n138_detail.reason="aggregate-budget";
            n138_detail.value=-ETIMEDOUT;}
        return false;
    }
    return true;
}
bool n138_user_begin(void)
{
    unsigned long flags;bool allowed;
    spin_lock_irqsave(&n138_lock,flags);
    allowed=n138_open_locked() || n138_is_proof();
    if(allowed)allowed=n138_ticket_locked();
    spin_unlock_irqrestore(&n138_lock,flags);return allowed;
}
void n138_user_end(void)
{
    unsigned long flags;struct n138_context *context;
    spin_lock_irqsave(&n138_lock,flags);
    context=n138_context_locked();
    if(n138_active && context){
        context->depth--;n138_active--;
        if(!context->depth)context->task=NULL;
    }else n138_history|=1;
    spin_unlock_irqrestore(&n138_lock,flags);
}
bool n138_access_begin(unsigned int family,unsigned int id)
{
    unsigned long flags;bool allowed;
    spin_lock_irqsave(&n138_lock,flags);
    allowed=n138_open_locked() || (n138_is_proof() && n138_proof_budget_locked() &&
        ((n138_selected_family==(int)family && n138_selected_id==(int)id) ||
         (family==N138_DP && id==0 && n138_link_access) ||
         (family==N138_DECON_SHARED_ACCESS && id==0 && n138_selected_family==N138_DECON &&
          (n138_selected_id==0 || (n138_selected_id==2 && n138_shared_te)))));
    if(allowed)allowed=n138_ticket_locked();
    if(!allowed && n138_closed){
        n138_history|=32;
        if(!n138_fault_errno)n138_fault_errno=-EACCES;
        if(!n138_detail.reason){n138_detail.reason=n138_fault_errno==-ETIMEDOUT?"aggregate-budget":"proof-access-denied";
            n138_detail.item=id;n138_detail.state=family;n138_detail.value=n138_fault_errno;}
    }
    spin_unlock_irqrestore(&n138_lock,flags);return allowed;
}
bool n138_dpp_write_begin(unsigned int id,u32 reg)
{
    unsigned long flags;bool allowed;
    spin_lock_irqsave(&n138_lock,flags);
    allowed=id<6 && ((n138_open_locked() &&
        ((!in_interrupt() && n138_dpp_writer[id]==current) ||
         (in_interrupt() && reg==4))) ||
        (n138_closed && n138_is_proof() && n138_proof_budget_locked() &&
         n138_selected_family==N138_DPP && n138_selected_id==(int)id));
    if(allowed)allowed=n138_ticket_locked();
    if(!allowed && !n138_closed)n138_history|=16;
    else if(!allowed && n138_closed){
        n138_history|=32;
        if(!n138_fault_errno)n138_fault_errno=-EACCES;
        if(!n138_detail.reason){n138_detail.reason=n138_fault_errno==-ETIMEDOUT?"aggregate-budget":"proof-access-denied";
            n138_detail.item=id;n138_detail.state=reg;n138_detail.value=n138_fault_errno;}
    }
    spin_unlock_irqrestore(&n138_lock,flags);return allowed;
}
bool n138_dpp_transaction_begin(unsigned int id)
{
    unsigned long flags;bool allowed;
    spin_lock_irqsave(&n138_lock,flags);
    allowed=id<6 && n138_open_locked() && !in_interrupt() &&
        n138_find(N138_DPP,id)->lifetime==N138_BOUND &&
        n138_find(N138_DPP,id)->probe_completed && !n138_dpp_writer[id];
    if(allowed)n138_dpp_writer[id]=current;else n138_history|=16;
    spin_unlock_irqrestore(&n138_lock,flags);return allowed;
}
void n138_dpp_transaction_end(unsigned int id)
{
    unsigned long flags;
    spin_lock_irqsave(&n138_lock,flags);
    if(id<6 && n138_dpp_writer[id]==current)n138_dpp_writer[id]=NULL;
    else n138_history|=16;
    spin_unlock_irqrestore(&n138_lock,flags);
}
bool n138_secure_begin(void)
{
    unsigned long flags;bool allowed;
    spin_lock_irqsave(&n138_lock,flags);
    /* Irreversible even if the native transition subsequently fails. */
    n138_history|=2;
    allowed=n138_open_locked();
    if(allowed)allowed=n138_ticket_locked();
    spin_unlock_irqrestore(&n138_lock,flags);return allowed;
}
void n138_invalid(void)
{
    unsigned long flags;
    spin_lock_irqsave(&n138_lock,flags);n138_history|=4;
    spin_unlock_irqrestore(&n138_lock,flags);
}
void n138_unowned_config(void) { n138_invalid(); }
int n138_probe(unsigned int family,unsigned int id,struct device *dev,void *object,void *subdev)
{
    struct n138_slot *slot=n138_find(family,id);unsigned long flags;int error=0;
    spin_lock_irqsave(&n138_lock,flags);
    if(!slot || !dev || !object || (family==N138_DPP && !subdev) || !n138_open_locked() || slot->lifetime){
        n138_history|=4;error=-ENODEV;
    }else{
        /* Persistent OWN struct-device reference, not a devres/private pin.
         * Private pointers are dereferenced only under the core device lock. */
        slot->dev=get_device(dev);slot->object=object;slot->subdev=subdev;slot->family=family;slot->id=id;
        slot->probe_task=current;slot->lifetime=N138_PROBING;slot->generation++;
    }
    spin_unlock_irqrestore(&n138_lock,flags);return error;
}
int n138_resources(unsigned int family,unsigned int id,void *object)
{
    struct n138_slot *slot=n138_find(family,id);unsigned long flags;int error=0;
    const struct n138_native_ops *ops=NULL;struct n136_detail detail={0};
    spin_lock_irqsave(&n138_lock,flags);
    if(!slot || slot->object!=object || slot->probe_task!=current ||
       slot->lifetime!=N138_PROBING || !n138_open_locked())error=-ENODEV;
    spin_unlock_irqrestore(&n138_lock,flags);
    if(error){n138_invalid();return error;}
    switch(family){
    case N138_DECON:ops=n138_decon_native();break;
    case N138_DPP:ops=n138_dpp_native();break;
    case N138_DP:ops=n138_dp_native();break;
    case N138_DSIM:ops=n138_dsim_native();break;
    default:break;
    }
    if(!ops || ops->validate(slot,&detail)){n138_invalid();return -ENODEV;}
    spin_lock_irqsave(&n138_lock,flags);
    if(!slot || slot->object!=object || slot->probe_task!=current ||
       slot->lifetime!=N138_PROBING || !n138_open_locked()){
        n138_history|=4;error=-ENODEV;
    }else{slot->lifetime=N138_RESOURCES;slot->generation++;}
    spin_unlock_irqrestore(&n138_lock,flags);return error;
}
int n138_ready(unsigned int family,unsigned int id,void *object)
{
    struct n138_slot *slot=n138_find(family,id);unsigned long flags;int error=0;
    spin_lock_irqsave(&n138_lock,flags);
    if(!slot || slot->object!=object || slot->probe_task!=current ||
       slot->lifetime!=N138_RESOURCES || !n138_open_locked()){
        n138_history|=4;error=-ENODEV;
    }else{
        slot->lifetime=N138_BOUND;
        slot->bound_driver=slot->dev->driver;slot->generation++;
    }
    spin_unlock_irqrestore(&n138_lock,flags);return error;
}
void n138_probe_result(struct device *dev,bool success)
{
    unsigned long flags;unsigned int i;
    spin_lock_irqsave(&n138_lock,flags);
    for(i=0;i<N138_SLOTS;i++)if(n138_slots[i].dev==dev){
        if(success && n138_open_locked() && n138_slots[i].lifetime==N138_BOUND &&
           n138_slots[i].probe_task==current){
            n138_slots[i].probe_completed=true;n138_slots[i].probe_task=NULL;
            n138_slots[i].generation++;
        }else{
            n138_slots[i].lifetime=N138_INVALID;n138_slots[i].generation++;
            n138_history|=4;
        }
    }
    if(!success)n138_history|=4;
    spin_unlock_irqrestore(&n138_lock,flags);
}
void n138_detach(struct device *dev)
{
    unsigned long flags;unsigned int i;
    spin_lock_irqsave(&n138_lock,flags);
    n138_history|=4;
    for(i=0;i<N138_SLOTS;i++)if(n138_slots[i].dev==dev){
        n138_slots[i].lifetime=N138_INVALID;n138_slots[i].generation++;
    }
    spin_unlock_irqrestore(&n138_lock,flags);
}
void n138_config_end(struct n138_config_guard *guard)
{
    if(guard->channel_core){device_unlock(guard->channel->dev);guard->channel_core=false;}
    if(guard->owner_core){device_unlock(guard->owner->dev);guard->owner_core=false;}
    if(guard->admitted){n138_user_end();guard->admitted=false;}
}
int n138_config_begin(void *owner,void *subdev,struct n138_config_guard *guard)
{
    unsigned long flags;unsigned int i;bool inherited=false;int error=0;
    memset(guard,0,sizeof(*guard));
    if(!n138_user_begin())return -ESHUTDOWN;
    guard->admitted=true;
    spin_lock_irqsave(&n138_lock,flags);
    for(i=0;i<3;i++)if(n138_slots[i].object==owner)guard->owner=&n138_slots[i];
    for(i=3;i<9;i++)if(n138_slots[i].subdev==subdev)guard->channel=&n138_slots[i];
    if(!owner || !subdev || !guard->owner || !guard->channel ||
       guard->channel->lifetime!=N138_BOUND || !guard->channel->probe_completed)
        error=-ENODEV;
    if(!error){
        inherited=guard->owner->lifetime==N138_RESOURCES &&
            guard->owner->probe_task==current && !guard->owner->probe_completed;
        if(!inherited && (guard->owner->lifetime!=N138_BOUND || !guard->owner->probe_completed))error=-EPERM;
    }
    spin_unlock_irqrestore(&n138_lock,flags);
    if(error)goto refused;
    /* Only the exact resource-validated probe task inherits the core lock
     * already held by driver_probe_device. Never try/unlock that same level. */
    if(!inherited){
        if(!device_trylock(guard->owner->dev)){error=-EBUSY;goto refused;}
        guard->owner_core=true;
    }
    if(!device_trylock(guard->channel->dev)){error=-EBUSY;goto refused;}
    guard->channel_core=true;
    spin_lock_irqsave(&n138_lock,flags);
    if(!n138_open_locked() || guard->channel->lifetime!=N138_BOUND || !guard->channel->probe_completed ||
       guard->channel->dev->driver!=n138_dpp_native()->driver ||
       dev_get_drvdata(guard->channel->dev)!=guard->channel->object ||
       guard->owner->dev->driver!=n138_decon_native()->driver ||
       dev_get_drvdata(guard->owner->dev)!=guard->owner->object ||
       (!inherited && (guard->owner->lifetime!=N138_BOUND || !guard->owner->probe_completed)) ||
       (inherited && (guard->owner->lifetime!=N138_RESOURCES || guard->owner->probe_task!=current)))
        error=-ENODEV;
    spin_unlock_irqrestore(&n138_lock,flags);
    if(!error)return 0;
refused:
    if(error!=-EBUSY)n138_invalid();
    n138_config_end(guard);return error;
}
bool n138_borrow(unsigned int id,void *decon)
{
    struct n138_slot *channel=n138_find(N138_DPP,id),*owner=NULL;
    unsigned long flags;unsigned int i;bool allowed=false;
    spin_lock_irqsave(&n138_lock,flags);
    for(i=0;i<3;i++)if(n138_slots[i].object==decon){owner=&n138_slots[i];break;}
    if(n138_open_locked() && channel && channel->lifetime==N138_BOUND && channel->probe_completed && owner &&
       ((owner->lifetime==N138_BOUND && owner->probe_completed) || (owner->lifetime==N138_RESOURCES &&
        owner->probe_task==current)) &&
       (!channel->borrower || channel->borrower==decon)){
        /* Set before copying the native pointer or touching any register.
         * Normal software OFF/mask overwrites never erase this lease. */
        channel->borrower=decon;allowed=true;
    }else n138_history|=8;
    spin_unlock_irqrestore(&n138_lock,flags);return allowed;
}
bool n138_lease_matches(unsigned int id,void *decon)
{
    struct n138_slot *slot=n138_find(N138_DPP,id);
    return slot && slot->lifetime==N138_BOUND && slot->probe_completed && slot->borrower==decon;
}
bool n138_proving(void) { return n138_closed && n138_is_proof(); }
bool n138_budget(void)
{
    if(!n138_proving())return true;
    if(READ_ONCE(n138_history) || !n138_polls || ktime_get_ns()>=n138_deadline)return false;
    n138_polls--;return true;
}
int n138_checkpoint(void)
{
    unsigned int history;unsigned long flags;int error;
    if(!n138_proving())return 0;
    history=READ_ONCE(n138_history);
    if(history){
        if(!n138_detail.reason){n138_detail.reason="proof-history";
            n138_detail.state=history;n138_detail.value=-EACCES;}
        return READ_ONCE(n138_fault_errno)?READ_ONCE(n138_fault_errno):-EACCES;
    }
    if(n138_budget())return 0;
    spin_lock_irqsave(&n138_lock,flags);
    if(n138_history)error=n138_fault_errno?n138_fault_errno:-EACCES;
    else{n138_history|=64;n138_fault_errno=-ETIMEDOUT;error=-ETIMEDOUT;}
    spin_unlock_irqrestore(&n138_lock,flags);return error;
}
int n138_poll_failure(const char *reason,unsigned int id,u32 state,int error)
{
    if(n138_proving() && !n138_detail.reason){
        n138_detail.reason=reason;n138_detail.item=id;n138_detail.state=state;
        n138_detail.value=error;
    }
    return error;
}
int n138_refuse_access(const char *reason,unsigned int id,u32 state)
{
    unsigned long flags;
    spin_lock_irqsave(&n138_lock,flags);n138_history|=32;
    if(!n138_fault_errno)n138_fault_errno=-EPERM;
    if(!n138_detail.reason){n138_detail.reason=reason;n138_detail.item=id;
        n138_detail.state=state;n138_detail.value=-EPERM;}
    spin_unlock_irqrestore(&n138_lock,flags);return -EPERM;
}
void n138_resolved_failure(void)
{
    /* Native instant-stop ACK resolved its preceding per-frame timeout.
     * A later reset failure must retain its own first inspected value. */
    if(n138_proving() && !READ_ONCE(n138_history))memset(&n138_detail,0,sizeof(n138_detail));
}
bool n138_dp_accessible(void)
{
    struct n138_slot *slot=n138_find(N138_DP,0);
    return n138_proving() && slot->lifetime==N138_BOUND && slot->device_locked &&
        slot->pm_owned && slot->generation==slot->frozen_generation &&
        n138_native_dp_link_ready(slot->object);
}
int n138_shared_te_begin(void)
{
    struct n138_slot *primary=n138_find(N138_DECON,0);unsigned int i;
    if(!n138_proving() || n138_selected_family!=N138_DECON || n138_selected_id!=2 ||
       !primary->device_locked || primary->lifetime!=N138_BOUND || !primary->probe_completed ||
       primary->generation!=primary->frozen_generation || !primary->stopped)
        return n138_refuse_access("shared-te-owner",2,0);
    for(i=0;i<N138_SLOTS;i++)if(n138_slots[i].lifetime &&
        (!n138_slots[i].device_locked || !n138_slots[i].locked))
        return n138_refuse_access("shared-te-peer-lock",i,0);
    n138_shared_te=true;return 0;
}
void n138_shared_te_end(void) { if(n138_proving())n138_shared_te=false; }
static int n138_nodes(const struct n138_native_ops *ops)
{
    struct device_node *node;unsigned int count=0;int id;
    for_each_compatible_node(node,NULL,ops->compatible){
        struct n138_slot *slot;
        if(!of_device_is_available(node))continue;
        id=ops->alias?of_alias_get_id(node,ops->alias):0;
        slot=id<0?NULL:n138_find(ops->family,id);
        if(!slot || !slot->dev || slot->dev->of_node!=node ||
           slot->lifetime!=N138_BOUND || !slot->probe_completed){of_node_put(node);return -ENODEV;}
        count++;
    }
    if(!count)return -ENODEV;
    for(id=0;id<(int)ops->count;id++){
        struct n138_slot *slot=n138_find(ops->family,id);
        if(slot->lifetime && (!slot->dev || !of_device_is_available(slot->dev->of_node)))return -ENODEV;
    }
    return 0;
}
int n138_display_prepare(void)
{
    const struct n138_native_ops *ops[4];struct n138_slot *slot;
    unsigned long flags;unsigned int family,id,i;int error=0,mode=-1,owned=0;
    const char *stage="display-freeze";
    spin_lock_irqsave(&n138_lock,flags);
    if(n138_seen){spin_unlock_irqrestore(&n138_lock,flags);return -EALREADY;}
    n138_seen=true;n138_closed=true;
    if(n138_active || n138_history){
        n138_aborting=n138_active!=0;
        error=-EBUSY;n138_detail.reason="admission-history";
        n138_detail.state=n138_active;n138_detail.aux=n138_history;
    }
    spin_unlock_irqrestore(&n138_lock,flags);
    if(error)goto refused;
    n138_deadline=ktime_get_ns()+N138_BUDGET_NS;n138_polls=N138_POLL_LIMIT;
    ops[0]=n138_decon_native();ops[1]=n138_dpp_native();
    ops[2]=n138_dp_native();ops[3]=n138_dsim_native();
    stage="display-owners";
    for(family=0;family<4;family++){
        if(!ops[family] || ops[family]->family!=family ||
           ops[family]->count!=n138_counts[family]){error=-ENODEV;goto release;}
        error=n138_nodes(ops[family]);if(error)goto release;
        for(id=0;id<ops[family]->count;id++){
            slot=n138_find(family,id);if(!slot->lifetime)continue;
            n138_detail.item=(family<<8)|id;
            if(slot->lifetime!=N138_BOUND || !slot->probe_completed || !slot->dev){error=-ENODEV;goto release;}
            if(!device_trylock(slot->dev)){error=-EBUSY;goto release;}
            slot->device_locked=true;
            spin_lock_irqsave(&n138_lock,flags);
            if(n138_history || slot->lifetime!=N138_BOUND || !slot->probe_completed ||
               slot->dev->driver!=ops[family]->driver || slot->dev->driver!=slot->bound_driver ||
               dev_get_drvdata(slot->dev)!=slot->object)error=-ENODEV;
            else slot->frozen_generation=slot->generation;
            spin_unlock_irqrestore(&n138_lock,flags);
            if(error)goto release;
            error=ops[family]->validate(slot,&n138_detail);if(error)goto release;
            error=ops[family]->lock(slot,&n138_detail);if(error)goto release;
            slot->locked=true;
        }
    }
    for(id=0;id<6;id++){
        bool found=false;
        slot=n138_find(N138_DPP,id);
        if(!slot->lifetime || !slot->borrower)continue;
        for(i=0;i<3;i++)if(n138_slots[i].lifetime==N138_BOUND &&
            n138_slots[i].object==slot->borrower)found=true;
        if(!found){error=-EPERM;n138_detail.reason="borrower-not-bound";goto release;}
    }
    /* Every registered peer has stable native binding and locks before any
     * callback cancellation, IRQ action, PM reference or controller write. */
    stage="display-queues";
    for(family=0;family<4;family++)for(id=0;id<ops[family]->count;id++){
        slot=n138_find(family,id);if(!slot->lifetime)continue;
        error=ops[family]->quiet(slot,&n138_detail);if(error)goto release;
    }
    stage="display-access";
    for(i=0;i<N138_SLOTS;i++){
        slot=&n138_slots[i];if(!slot->lifetime || slot->family==N138_DPP)continue;
        error=pm_runtime_get_if_in_use(slot->dev);
        if(error<0){n138_detail.reason="power-reference";goto release;}
        slot->pm_owned=error==1;
        if(slot->pm_owned &&
           ((slot->family==N138_DSIM && n138_native_dsim_link_ready(slot->object)) ||
            (slot->family==N138_DP && n138_native_dp_link_ready(slot->object))))owned++;
    }
    mode=n136_cal_begin(N138_DPU_DOMAINS,&n138_detail);
    if(mode<0){error=mode;goto release;}
    n138_cal_reserved=true;
    if(mode && !owned){error=-EHOSTDOWN;n138_detail.reason="no-existing-access-lease";goto release;}
    /* Exact native PMU OFF never samples any powered-off DPU/DP SFR. */
    if(mode){
        n138_proof_task=current;
        stage="display-decon-stop";
        for(family=0;family<2;family++)for(id=0;id<ops[family]->count;id++){
            slot=n138_find(family,id);if(!slot->lifetime)continue;
            error=n138_checkpoint();
            if(error){if(!n138_detail.reason)n138_detail.reason="aggregate-budget";goto release;}
            n138_selected_family=family;n138_selected_id=id;
            n138_link_access=family==N138_DECON && id==2 && n138_dp_accessible();
            n138_detail.reason=NULL;
            if(family==N138_DPP)stage="display-dpp-reset";
            error=ops[family]->stop(slot,&n138_detail);if(error)goto release;
            /* A denied accessor must not turn a native zero-return/clear bit
             * into an ACK. No lease/state/cache success precedes this check. */
            if(READ_ONCE(n138_history)){
                error=READ_ONCE(n138_fault_errno)?READ_ONCE(n138_fault_errno):-EACCES;goto release;
            }
            slot->stopped=true;
        }
        n138_selected_family=-1;n138_selected_id=-1;n138_link_access=false;n138_shared_te=false;
        n138_proof_task=NULL;
    }
    spin_lock_irqsave(&n138_lock,flags);
    if(n138_active || n138_history)error=-EBUSY;
    spin_unlock_irqrestore(&n138_lock,flags);
    if(error)goto release;
    n136_cal_end(N138_DPU_DOMAINS,true);n138_cal_reserved=false;
    slot=n138_find(N138_DP,0);
    error=n136_witness_commit(&n138_witness,slot->dev,
        mode?N138_DPU_NATIVE_STOP_FROZEN:N138_DPU_DOMAIN_OFF_FROZEN,N138_DPU_DOMAINS);
    if(!error)error=n130_dma_record(slot->dev,0);
    if(!error)n138_complete=true;
release:
    n138_selected_family=-1;n138_selected_id=-1;n138_link_access=false;n138_shared_te=false;
    n138_proof_task=NULL;
    if(n138_cal_reserved){n136_cal_end(N138_DPU_DOMAINS,false);n138_cal_reserved=false;}
    for(i=N138_SLOTS;i;i--){
        slot=&n138_slots[i-1];
        /* Only our successful non-resuming increment; no callback/power action. */
        if(slot->pm_owned){pm_runtime_put_noidle(slot->dev);slot->pm_owned=false;}
        if(slot->locked){ops[slot->family]->unlock(slot);slot->locked=false;}
        if(slot->device_locked){device_unlock(slot->dev);slot->device_locked=false;}
    }
refused:
    spin_lock_irqsave(&n138_lock,flags);n138_result=error;
    spin_unlock_irqrestore(&n138_lock,flags);
    if(error){
        n131_gate_refused(stage,error,n138_find(N138_DP,0)->dev);
        pr_emerg("N10XNU138 id=%s display reason=%.40s item=%u state=%u value=%d aux=%u owner=%.64s\n",
            N10_KEXEC_BUILD_ID,n138_detail.reason?n138_detail.reason:"native-binding",
            n138_detail.item,n138_detail.state,n138_detail.value,n138_detail.aux,
            n138_find(N138_DP,0)->dev?dev_name(n138_find(N138_DP,0)->dev):"none");
    }
    return error;
}
static int n138_display_cached(struct device *owner)
{
    const struct n138_native_ops *ops[4];unsigned long flags;unsigned int i;int error=0;
    struct n138_slot *slot=n138_find(N138_DP,0);
    spin_lock_irqsave(&n138_lock,flags);
    if(!n138_seen || !n138_complete || n138_result || !n138_closed ||
       n138_active || n138_history || slot->dev!=owner)error=-EPERM;
    spin_unlock_irqrestore(&n138_lock,flags);
    if(error)return error;
    ops[0]=n138_decon_native();ops[1]=n138_dpp_native();
    ops[2]=n138_dp_native();ops[3]=n138_dsim_native();
    for(i=0;i<N138_SLOTS;i++){
        slot=&n138_slots[i];if(!slot->lifetime)continue;
        /* No private or mapped-resource dereference before this core lock.
         * A concurrent remove/probe must fail this bounded acquisition or the
         * exact generation/binding comparison, even if remove ignored errno. */
        if(!device_trylock(slot->dev)){error=-EBUSY;break;}
        slot->device_locked=true;
        spin_lock_irqsave(&n138_lock,flags);
        if(n138_history || slot->lifetime!=N138_BOUND || !slot->probe_completed ||
           slot->generation!=slot->frozen_generation ||
           slot->dev->driver!=slot->bound_driver ||
           slot->dev->driver!=ops[slot->family]->driver ||
           dev_get_drvdata(slot->dev)!=slot->object)error=-ENODEV;
        spin_unlock_irqrestore(&n138_lock,flags);
        if(error)break;
        error=ops[slot->family]->validate(slot,&n138_detail);if(error)break;
    }
    if(!error && !n136_witness_valid(&n138_witness,owner,n138_witness.type,N138_DPU_DOMAINS))error=-EPERM;
    if(!error){
        spin_lock_irqsave(&n138_lock,flags);
        if(n138_history || n138_active)error=-EBUSY;
        else n138_core_owner=current;
        spin_unlock_irqrestore(&n138_lock,flags);
    }
    if(error)for(i=N138_SLOTS;i;i--){
        slot=&n138_slots[i-1];
        if(slot->device_locked){device_unlock(slot->dev);slot->device_locked=false;}
    }
    /* Success intentionally retains OWN core locks through the remaining
     * terminal IOMMU/final transfer path; no subsequent device_shutdown call.
     * Private/devres lifetime therefore cannot race the cached witness. */
    return error;
}
int n138_display_final(void)
{
    struct device *owner=n138_find(N138_DP,0)->dev;
    unsigned long flags;int error;
    spin_lock_irqsave(&n138_lock,flags);
    if(n138_final_seen){
        error=n138_core_owner==current && !n138_history ? n138_final_result : -EPERM;
        spin_unlock_irqrestore(&n138_lock,flags);return error;
    }
    n138_final_seen=true;spin_unlock_irqrestore(&n138_lock,flags);
    error=n138_display_cached(owner);
    spin_lock_irqsave(&n138_lock,flags);n138_final_result=error;
    spin_unlock_irqrestore(&n138_lock,flags);
    if(error){
        if(owner)(void)n130_dma_record(owner,error);
        n131_gate_refused("display-cached",error,owner);
    }
    return error;
}
int n138_display_unwind(void)
{
    unsigned long flags,owned=0;unsigned int i;
    spin_lock_irqsave(&n138_lock,flags);
    if(n138_core_owner && n138_core_owner!=current){
        spin_unlock_irqrestore(&n138_lock,flags);return -EPERM;
    }
    if(n138_core_owner==current){
        for(i=0;i<N138_SLOTS;i++)if(n138_slots[i].device_locked){
            owned|=1UL<<i;n138_slots[i].device_locked=false;
        }
        n138_core_owner=NULL;
    }
    spin_unlock_irqrestore(&n138_lock,flags);
    for(i=N138_SLOTS;i;i--)if(owned&(1UL<<(i-1)))device_unlock(n138_slots[i-1].dev);
    /* Admissions, CAL closure, hardware ACK, leases and mapped buffers stay
     * terminal. This releases only the caller's acquired core lock levels. */
    return 0;
}
