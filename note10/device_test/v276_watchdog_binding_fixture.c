/* SPDX-License-Identifier: GPL-2.0-only */
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "v276_watchdog_binding.h"
#define LITTLE_CLUSTER 0
#define DEFINE_SPINLOCK(name) int name
static int context_ok=1,interrupt_context,locks,hardware_calls;
static void (*inject_before_lock)(void);
static void spin_lock(int *lock){void (*inject)(void)=inject_before_lock;inject_before_lock=NULL;if(inject)inject();if(*lock)locks=-1000;*lock=1;++locks;}
static int spin_trylock(int *lock){if(*lock)return 0;spin_lock(lock);return 1;}
static void spin_unlock(int *lock){*lock=0;--locks;}
#define in_interrupt() interrupt_context
#define preemptible() context_ok
#define IS_ERR_OR_NULL(p) (!(p)||(uintptr_t)(p)>UINTPTR_MAX-4095U)
struct s3c2410_wdt;
struct variant {int (*pmu_reset_func)(struct s3c2410_wdt *,bool);};
static int s3c2410wdt_noncpu_int_en(struct s3c2410_wdt *p,bool b){(void)p;(void)b;++hardware_calls;return 0;}
static const struct variant drv_data_exynos9_v1={s3c2410wdt_noncpu_int_en},drv_data_exynos9_v2={s3c2410wdt_noncpu_int_en};
struct watchdog_ops {int marker;};
static const struct watchdog_ops s3c2410wdt_ops={1},foreign_ops={2};
struct watchdog_device {const struct watchdog_ops *ops;void *driver_data,*wd_data;int id;};
static void *watchdog_get_drvdata(struct watchdog_device *wdd){return wdd->driver_data;}
static int soft_noboot;
struct s3c2410_wdt {unsigned int cluster;const struct variant *drv_data;unsigned long freq;struct watchdog_device wdt_device;void *rate_clock,*gate_clock;int use_multistage_wdt;};
#include "v276_watchdog_driver.inc"
static struct s3c2410_wdt w;
static void fresh(void){n269_empty(&n269_cache,N269_UNSEEN,0);n269_cache_lock=0;locks=0;hardware_calls=0;inject_before_lock=NULL;context_ok=1;interrupt_context=0;memset(&w,0,sizeof(w));w.drv_data=&drv_data_exynos9_v1;w.freq=26000000;w.rate_clock=(void *)1;w.gate_clock=(void *)1;w.wdt_device.ops=&s3c2410wdt_ops;w.wdt_device.driver_data=&w;w.wdt_device.id=-1;}
static void complete(unsigned int id){w.wdt_device.wd_data=(void *)1;w.wdt_device.id=(int)id;n276_core_registered(&w.wdt_device);}
static void interleave(void){complete(9);}
static int qualified(const struct n269_binding *v){return v->schema==2&&v->state==N269_PUBLISHED&&v->flags==63&&v->watchdog_id_at_core_registration!=UINT32_MAX&&v->error_code==0&&v->reserved==0;}
#define CHECK(x) do{if(!(x)){fprintf(stderr,"new276 predicate %d\n",__LINE__);return 1;}}while(0)
int main(void)
{
    struct n269_binding out;unsigned int token;struct s3c2410_wdt other;
    fresh();token=n269_begin();n269_publish(token,&w);CHECK(!n269_snapshot(&out)&&!qualified(&out)&&!(out.flags&N269_CORE));complete(7);CHECK(!n269_snapshot(&out)&&qualified(&out)&&out.watchdog_id_at_core_registration==7&&sizeof(out)==40&&__alignof__(out)==8&&locks==0&&!hardware_calls);puts("N276CASE deferred=PASS");
    fresh();token=n269_begin();complete(3);CHECK(n269_snapshot(&out)==-EINPROGRESS&&(out.flags&N269_CORE)&&!qualified(&out));n269_publish(token,&w);CHECK(!n269_snapshot(&out)&&qualified(&out)&&out.watchdog_id_at_core_registration==3&&locks==0&&!hardware_calls);puts("N276CASE immediate=PASS");
    fresh();token=n269_begin();inject_before_lock=interleave;n269_publish(token,&w);CHECK(!n269_snapshot(&out)&&qualified(&out)&&out.watchdog_id_at_core_registration==9&&locks==0&&!hardware_calls);puts("N276CASE sample-commit=PASS");
    fresh();token=n269_begin();n269_publish(token,&w);CHECK(!n269_snapshot(&out)&&!qualified(&out));if(token==1)n269_remove(&w);complete(4);n269_publish(token,&w);CHECK(n269_snapshot(&out)==-ENODEV&&out.state==N269_REMOVED&&!(out.flags&N269_CORE));
    fresh();token=n269_begin();complete(4);if(token==1)n269_remove(&w);n269_publish(token,&w);CHECK(n269_snapshot(&out)==-ENODEV&&!qualified(&out)&&out.watchdog_id_at_core_registration==UINT32_MAX);
    fresh();token=n269_begin();n269_publish(token,&w);complete(4);n269_remove(&w);complete(4);CHECK(n269_snapshot(&out)==-ENODEV&&!qualified(&out)&&locks==0&&!hardware_calls);puts("N276CASE failure-remove=PASS");
    fresh();token=n269_begin();complete(1);CHECK(n269_begin()==0);n269_publish(token,&w);complete(1);CHECK(n269_snapshot(&out)==-EEXIST&&out.state==N269_AMBIGUOUS&&out.flags==0);
    fresh();token=n269_begin();n269_publish(token,&w);complete(1);complete(1);CHECK(!n269_snapshot(&out)&&qualified(&out));complete(2);n269_remove(&w);CHECK(n269_snapshot(&out)==-EEXIST&&out.flags==0&&n269_begin()==0&&locks==0&&!hardware_calls);puts("N276CASE duplicate=PASS");
    fresh();token=n269_begin();n276_core_registered(NULL);w.wdt_device.ops=&foreign_ops;complete(1);w.wdt_device.ops=&s3c2410wdt_ops;w.wdt_device.driver_data=NULL;complete(1);w.wdt_device.driver_data=&w;other=w;n276_core_registered(&other.wdt_device);w.cluster=1;complete(1);w.cluster=0;w.drv_data=NULL;complete(1);w.drv_data=&drv_data_exynos9_v1;w.wdt_device.wd_data=NULL;n276_core_registered(&w.wdt_device);w.wdt_device.wd_data=(void *)1;w.wdt_device.id=-1;n276_core_registered(&w.wdt_device);CHECK(n269_snapshot(&out)==-EINPROGRESS&&out.flags==0&&out.watchdog_id_at_core_registration==UINT32_MAX&&locks==0&&!hardware_calls&&token==1);puts("N276CASE identity=PASS");
    return 0;
}
