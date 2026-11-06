/* SPDX-License-Identifier: GPL-2.0-only */
/* Same native CAL TU: no power action, no clock-state inference. */
#include <linux/mutex.h>
#include <linux/spinlock.h>
#include <linux/smp.h>
#include <linux/device.h>
#include <linux/printk.h>
#include <linux/string.h>
#include <linux/v136_terminal.h>
#include <linux/note10_legacy_kexec_build.h>
#if !defined(CONFIG_NOTE10_XNU_KEXEC_HANDOFF) || CONFIG_NOTE10_XNU_KEXEC_HANDOFF != 1 || !defined(CONFIG_PMUCAL) || !defined(CONFIG_SOC_EXYNOS9820) || defined(CONFIG_SOC_EXYNOS9820_EVT0)
#error "v136 terminal witnesses require pinned Exynos9820 EVT1 CAL"
#endif
static DEFINE_MUTEX(n136_cal_lock);
static DEFINE_SPINLOCK(n136_cal_state_lock);
static unsigned int n136_closed_domains;
static unsigned int n136_reserved_domains;
static unsigned int n136_cal_domain(unsigned int id)
{
    unsigned int index=id&0xffffU;
    if((id&0xffff0000U)!=0xb1380000U)return 0;
    return index==1 || index==2 || index==4 || index==5 || index==6 ? 1U<<index : 0;
}
static int n136_cal_descriptor(unsigned int index,struct n136_detail *detail)
{
    static const u32 offsets[]={0,0x1d00,0x1d80,0,0x1e80,0x1f00,0x2300};
    static const char *const names[]={NULL,"blkpwr_npu0","blkpwr_npu1",NULL,"blkpwr_dspm","blkpwr_dsps","blkpwr_g2d"};
    struct pmucal_pd *pd;u32 value,request,status;
    detail->reason="cal-descriptor";detail->item=index;
    if(index>=pmucal_pd_list_size || index>=ARRAY_SIZE(offsets))return -ENODEV;
    pd=&pmucal_pd_list[index];
    if(pd->id!=index || !pd->name || strcmp(pd->name,names[index]) ||
       !pd->status || pd->num_status!=1 || pd->status[0].access_type!=PMUCAL_READ ||
       pd->status[0].base_pa!=0x15860000 || !pd->status[0].base_va ||
       pd->status[0].offset!=offsets[index]+4 || pd->status[0].mask!=1)return -ENODEV;
#ifdef CONFIG_PMUCAL_DBG
    if(!pd->dbg || pd->dbg->emul_offset!=offsets[index]+12 || pd->dbg->emul_bit)return -ENODEV;
    value=pd->dbg->emul_en|pd->dbg->emul_enabled;
    if(value){detail->reason="cal-emulation-user";detail->state=value;return -EBUSY;}
#endif
    /* Always-on native PMU mapping, not a powered-off domain CMU. Read once. */
    request=readl(pd->status[0].base_va+offsets[index]);
    status=readl(pd->status[0].base_va+offsets[index]+4);
    value=readl(pd->status[0].base_va+offsets[index]+12);
    if(value&1){detail->reason="cal-emulation";detail->state=value;detail->aux=offsets[index]+12;return -EBUSY;}
    if((request^status)&1){detail->reason="domain-transition";detail->state=request;detail->aux=status;return -EIO;}
    return status&1;
}
int n136_cal_begin(unsigned int domains,struct n136_detail *detail)
{
    unsigned int index;unsigned long flags;int mode=-1,current;bool busy;
    if(domains!=N136_NPU_DOMAINS && domains!=N136_SCORE_DOMAINS && domains!=N136_G2D_DOMAINS)return -EINVAL;
    if(!mutex_trylock(&n136_cal_lock)){detail->reason="cal-busy";return -EBUSY;}
    spin_lock_irqsave(&n136_cal_state_lock,flags);
    busy=((n136_closed_domains|n136_reserved_domains)&domains)!=0;
    spin_unlock_irqrestore(&n136_cal_state_lock,flags);
    if(busy){detail->reason="cal-already-frozen";mutex_unlock(&n136_cal_lock);return -EALREADY;}
    for(index=1;index<=6;index++)if(domains&(1U<<index)){
        current=n136_cal_descriptor(index,detail);
        if(current<0){mutex_unlock(&n136_cal_lock);return current;}
        if(mode>=0 && mode!=current){detail->reason="domain-mixed";detail->state=mode;detail->aux=current;mutex_unlock(&n136_cal_lock);return -EIO;}
        mode=current;
    }
    spin_lock_irqsave(&n136_cal_state_lock,flags);n136_reserved_domains|=domains;
    spin_unlock_irqrestore(&n136_cal_state_lock,flags);
    /* No PM callback or domain SFR access while holding this mutex. Native
     * recursive PM requests reject at the admission wrapper while reserved. */
    mutex_unlock(&n136_cal_lock);
    detail->reason=mode?"domains-on":"domains-off";detail->state=mode;return mode;
}
void n136_cal_end(unsigned int domains,bool commit)
{
    unsigned long flags;
    /* Commit/release never waits for another domain's native PM/SMC call. */
    spin_lock_irqsave(&n136_cal_state_lock,flags);
    if((n136_reserved_domains&domains)!=domains){spin_unlock_irqrestore(&n136_cal_state_lock,flags);return;}
    if(commit)WRITE_ONCE(n136_closed_domains,n136_closed_domains|domains);
    n136_reserved_domains&=~domains;
    spin_unlock_irqrestore(&n136_cal_state_lock,flags);
}
bool n136_cal_frozen(unsigned int domains)
{ return (READ_ONCE(n136_closed_domains)&domains)==domains; }
int n136_witness_commit(struct n136_witness *w,struct device *owner,unsigned int type,unsigned int domains)
{
    if(!owner || w->committed || !n136_cal_frozen(domains) ||
       !((type==N136_SCORE_RESET_DMA_FROZEN && domains==N136_SCORE_DOMAINS) ||
         (type==N136_G2D_FINITE_JOBS_FROZEN && domains==N136_G2D_DOMAINS) ||
         (type==N136_NPU_DOMAINS_OFF_FROZEN && domains==N136_NPU_DOMAINS) ||
         (type==N136_SCORE_DOMAINS_OFF_FROZEN && domains==N136_SCORE_DOMAINS) ||
         (type==N136_G2D_DOMAIN_OFF_FROZEN && domains==N136_G2D_DOMAINS)))return -EPERM;
    w->owner=owner;w->type=type;w->domains=domains;smp_store_release(&w->committed,true);
    pr_emerg("N10XNU136 id=%s terminal witness=%u domains=%u owner=%.64s\n",N10_KEXEC_BUILD_ID,type,domains,dev_name(owner));
    return 0;
}
bool n136_witness_valid(const struct n136_witness *w,struct device *owner,unsigned int type,unsigned int domains)
{ return smp_load_acquire(&w->committed) && w->owner==owner && w->type==type && w->domains==domains && n136_cal_frozen(domains); }
