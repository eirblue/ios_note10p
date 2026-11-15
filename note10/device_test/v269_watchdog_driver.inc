/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in the actual driver after its variant tables; no live pointer escapes. */
#include <linux/v269_watchdog_binding.h>
#ifdef __KERNEL__
#include <linux/preempt.h>
#include <linux/spinlock.h>
#include <linux/string.h>
#include <linux/errno.h>
#endif
static DEFINE_SPINLOCK(n269_cache_lock);
static struct n269_binding n269_cache={.schema=1,.watchdog_id_at_probe=~0U};
static __attribute__((noinline)) void n269_empty(struct n269_binding *out,unsigned int state,unsigned int error)
{
    memset(out,0,sizeof(*out));out->schema=1;out->state=state;
    out->error_code=error;out->watchdog_id_at_probe=~0U;
}
static __attribute__((noinline)) unsigned int n269_begin(void)
{
    unsigned int token=0;
    spin_lock(&n269_cache_lock);
    if(n269_cache.state==N269_UNSEEN){n269_empty(&n269_cache,N269_PROBING,EINPROGRESS);token=1;}
    else n269_empty(&n269_cache,N269_AMBIGUOUS,EEXIST);
    spin_unlock(&n269_cache_lock);return token;
}
static __attribute__((noinline)) void n269_publish(unsigned int token,const struct s3c2410_wdt *wdt)
{
    struct n269_binding sample;
    if(token!=1||!wdt||wdt->cluster!=LITTLE_CLUSTER)return;
    n269_empty(&sample,N269_PUBLISHED,0);sample.cluster=wdt->cluster;
    sample.variant=wdt->drv_data==&drv_data_exynos9_v1?1:wdt->drv_data==&drv_data_exynos9_v2?2:0;
    sample.probe_cached_rate_hz=wdt->freq;
    sample.flags=N269_TAIL|N269_REGISTER_OK;
    if(wdt->wdt_device.wd_data){sample.flags|=N269_CORE;sample.watchdog_id_at_probe=wdt->wdt_device.id;}
    if(!IS_ERR_OR_NULL(wdt->rate_clock))sample.flags|=N269_RATE;
    if(!IS_ERR_OR_NULL(wdt->gate_clock))sample.flags|=N269_GATE;
    if(wdt->drv_data&&wdt->drv_data->pmu_reset_func==s3c2410wdt_noncpu_int_en)sample.flags|=N269_CALLBACK;
    if(soft_noboot)sample.flags|=N269_SOFT;
    if(wdt->use_multistage_wdt)sample.flags|=N269_MULTI;
    spin_lock(&n269_cache_lock);
    if(n269_cache.state==N269_PROBING)n269_cache=sample;
    spin_unlock(&n269_cache_lock);
}
static __attribute__((noinline)) void n269_remove(const struct s3c2410_wdt *wdt)
{
    if(!wdt||wdt->cluster!=LITTLE_CLUSTER)return;
    spin_lock(&n269_cache_lock);
    if(n269_cache.state!=N269_AMBIGUOUS)n269_empty(&n269_cache,N269_REMOVED,ENODEV);
    spin_unlock(&n269_cache_lock);
}
__attribute__((noinline)) int n269_snapshot(struct n269_binding *out)
{
    int error;
    if(!out)return -EINVAL;
    n269_empty(out,N269_BAD_CONTEXT,EPERM);
    if(in_interrupt()||!preemptible())return -EPERM;
    n269_empty(out,N269_BUSY,EBUSY);
    if(!spin_trylock(&n269_cache_lock))return -EBUSY;
    *out=n269_cache;spin_unlock(&n269_cache_lock);
    error=out->state==N269_PUBLISHED?0:out->state==N269_AMBIGUOUS?EEXIST:out->state==N269_PROBING?EINPROGRESS:ENODEV;
    out->error_code=error;return -error;
}
#ifdef __KERNEL__
static __used __attribute__((noinline)) void n269_layout_witness(void)
{
    asm volatile(".globl n269_size_binding\n.equ n269_size_binding,%c0\n"
                 ".globl n269_align_binding\n.equ n269_align_binding,%c1\n"
                 : : "i"(sizeof(struct n269_binding)),"i"(__alignof__(struct n269_binding)));
}
#endif
