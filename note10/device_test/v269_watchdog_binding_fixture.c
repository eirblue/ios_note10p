/* SPDX-License-Identifier: GPL-2.0-only */
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "v269_watchdog_binding.h"
#define LITTLE_CLUSTER 0
#define DEFINE_SPINLOCK(name) int name
static int context_ok=1,interrupt_context,locks;
static void spin_lock(int *lock){if(*lock)locks=-1000;*lock=1;++locks;}
static int spin_trylock(int *lock){if(*lock)return 0;spin_lock(lock);return 1;}
static void spin_unlock(int *lock){*lock=0;--locks;}
#define in_interrupt() interrupt_context
#define preemptible() context_ok
#define IS_ERR_OR_NULL(p) (!(p)||(uintptr_t)(p)>UINTPTR_MAX-4095U)
struct s3c2410_wdt;
struct variant {int (*pmu_reset_func)(struct s3c2410_wdt *,bool);};
static int s3c2410wdt_noncpu_int_en(struct s3c2410_wdt *p,bool b){(void)p;(void)b;return 0;}
static const struct variant drv_data_exynos9_v1={s3c2410wdt_noncpu_int_en},drv_data_exynos9_v2={s3c2410wdt_noncpu_int_en};
static int soft_noboot;
struct s3c2410_wdt {unsigned int cluster;const struct variant *drv_data;unsigned long freq;
    struct {void *wd_data;int id;} wdt_device;void *rate_clock,*gate_clock;int use_multistage_wdt;};
#include "v269_watchdog_driver.inc"
static void fresh(void){n269_empty(&n269_cache,N269_UNSEEN,0);n269_cache_lock=0;locks=0;context_ok=1;interrupt_context=0;}
#define CHECK(x) do{if(!(x)){fprintf(stderr,"new269 predicate %d\n",__LINE__);return 1;}}while(0)
int main(void)
{
    struct n269_binding out;unsigned int token;struct s3c2410_wdt w={0,&drv_data_exynos9_v1,26000000,{(void *)1,0},(void *)1,(void *)1,0};
    CHECK(sizeof(out)==40&&__alignof__(out)==8&&offsetof(struct n269_binding,reserved)==36);puts("N269CASE ABI=PASS");
    fresh();CHECK(n269_snapshot(&out)==-ENODEV&&out.state==N269_UNSEEN);token=n269_begin();
    CHECK(token==1&&n269_snapshot(&out)==-EINPROGRESS&&out.state==N269_PROBING&&out.flags==0);puts("N269CASE incomplete=PASS");
    fresh();token=n269_begin();n269_publish(0,&w);CHECK(n269_snapshot(&out)==-EINPROGRESS);
    n269_publish(token,&w);CHECK(!n269_snapshot(&out)&&out.state==N269_PUBLISHED&&out.flags==63&&out.probe_cached_rate_hz==26000000&&out.reserved==0&&locks==0);puts("N269CASE matching-success=PASS");
    fresh();w.cluster=1;n269_publish(0,&w);n269_remove(&w);n269_remove(NULL);CHECK(n269_snapshot(&out)==-ENODEV);w.cluster=0;puts("N269CASE big-null=PASS");
    fresh();token=n269_begin();w.drv_data=NULL;w.wdt_device.wd_data=NULL;n269_publish(token,&w);CHECK(!n269_snapshot(&out)&&out.variant==0&&!(out.flags&(N269_CORE|N269_CALLBACK))&&out.watchdog_id_at_probe==UINT32_MAX);w.drv_data=&drv_data_exynos9_v1;w.wdt_device.wd_data=(void *)1;puts("N269CASE unsupported=PASS");
    fresh();token=n269_begin();CHECK(n269_begin()==0);n269_publish(token,&w);n269_remove(&w);CHECK(n269_begin()==0&&n269_snapshot(&out)==-EEXIST&&out.flags==0);
    fresh();token=n269_begin();n269_publish(token,&w);CHECK(n269_begin()==0&&n269_snapshot(&out)==-EEXIST);puts("N269CASE ambiguous=PASS");
    fresh();token=n269_begin();n269_publish(token,&w);n269_remove(&w);CHECK(n269_snapshot(&out)==-ENODEV&&out.state==N269_REMOVED&&out.flags==0);CHECK(n269_begin()==0);n269_publish(token,&w);CHECK(n269_snapshot(&out)==-EEXIST);puts("N269CASE remove-reprobe=PASS");
    fresh();n269_cache_lock=1;memset(&out,255,sizeof(out));CHECK(n269_snapshot(&out)==-EBUSY&&out.state==N269_BUSY&&out.flags==0&&out.probe_cached_rate_hz==0);n269_cache_lock=0;puts("N269CASE busy=PASS");
    fresh();context_ok=0;CHECK(n269_snapshot(&out)==-EPERM&&out.state==N269_BAD_CONTEXT&&locks==0);context_ok=1;interrupt_context=1;CHECK(n269_snapshot(&out)==-EPERM&&locks==0);puts("N269CASE context=PASS");
    return 0;
}
