/* Stored-state snapshot only: no MMIO, opens, clock changes or watchdog operations. */
#include <linux/n300_return_diagnostic.h>
#include <linux/string.h>
#include <linux/bug.h>
void noinline n300_wdt_snapshot(struct n300_wdt_fields *s)
{
    struct s3c2410_wdt *wdt=s3c_wdt[LITTLE_CLUSTER];
    BUILD_BUG_ON(LITTLE_CLUSTER!=N300_LITTLE_CLUSTER);
    BUILD_BUG_ON(S3C2410_WATCHDOG_DEFAULT_TIME!=N300_DEFAULT_TIMEOUT);
    memset(s,0,sizeof(*s));
    if(!wdt)return;
    s->present=1;s->soft_noboot=soft_noboot;s->nowayout=nowayout;s->cluster=wdt->cluster;
    s->variant=wdt->drv_data==&drv_data_exynos9_v1;
    s->route_func=wdt->drv_data && wdt->drv_data->pmu_reset_func==s3c2410wdt_noncpu_int_en;
    s->rate_clock=!!wdt->rate_clock;s->gate_clock=!!wdt->gate_clock;s->freq=wdt->freq;
    s->multistage=wdt->use_multistage_wdt;s->device_id=wdt->wdt_device.id;
    s->timeout=wdt->wdt_device.timeout;s->max_heartbeat=wdt->wdt_device.max_hw_heartbeat_ms;
    s->active=watchdog_active(&wdt->wdt_device);s->hw_running=watchdog_hw_running(&wdt->wdt_device);
}
int n299_wdt_eligible(void)
{
    struct n300_wdt_fields s;n300_wdt_snapshot(&s);
    return !n300_wdt_reasons(&s);
}
