/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in the actual pinned driver, with access to its real variant/clock. */
#include <linux/legacy_kexec_return.h>
int n10_wdt_stage_kexec_return(struct n10_wdt_witness *w)
{
    struct s3c2410_wdt *wdt=s3c_wdt[LITTLE_CLUSTER];u32 control,route;int result;
    if(!w || !wdt || soft_noboot || wdt->cluster!=LITTLE_CLUSTER ||
       wdt->drv_data!=&drv_data_exynos9_v1 ||
       wdt->drv_data->pmu_reset_func!=s3c2410wdt_noncpu_int_en ||
       !wdt->rate_clock || !wdt->gate_clock || !wdt->reg_base ||
       !wdt->freq || clk_get_rate(wdt->rate_clock)!=wdt->freq)return -ENODEV;
    result=wdt->drv_data->pmu_reset_func(wdt,false);if(result)return result;
    result=s3c2410wdt_keepalive_emergency(true,LITTLE_CLUSTER);if(result)return result;
    result=exynos_pmu_read(wdt->drv_data->noncpu_int_en,&route);if(result)return result;
    control=readl(wdt->reg_base+S3C2410_WTCON);
    w->present=1;w->variant_bound=1;w->enabled=!!(control&S3C2410_WTCON_ENABLE);
    w->reset_enabled=!!(control&S3C2410_WTCON_RSTEN);w->interrupt_only=!!(control&S3C2410_WTCON_INTEN);
    w->pmu_route_enabled=!!(route&(1U<<wdt->drv_data->mask_bit));w->clock_rate=wdt->freq;
    w->data=readl(wdt->reg_base+S3C2410_WTDAT);w->effective_timeout=wdt->wdt_device.timeout;
    if(w->data!=wdt->count)return -EIO;
    w->first_count=readl(wdt->reg_base+S3C2410_WTCNT);
    udelay(1000); /* Bounded qualification only; a slow clock refuses transfer. */
    w->last_count=readl(wdt->reg_base+S3C2410_WTCNT);
    return n10_watchdog_qualified(w);
}
