/* No register access, watchdog open, start, ping or clock changes. */
int n299_wdt_eligible(void)
{
    struct s3c2410_wdt *wdt=s3c_wdt[LITTLE_CLUSTER];
    return wdt && !soft_noboot && !nowayout && wdt->cluster==LITTLE_CLUSTER &&
        wdt->drv_data==&drv_data_exynos9_v1 &&
        wdt->drv_data->pmu_reset_func==s3c2410wdt_noncpu_int_en &&
        wdt->rate_clock && wdt->gate_clock && wdt->freq && !wdt->use_multistage_wdt &&
        wdt->wdt_device.id==0 && wdt->wdt_device.timeout==S3C2410_WATCHDOG_DEFAULT_TIME &&
        !wdt->wdt_device.max_hw_heartbeat_ms &&
        !watchdog_active(&wdt->wdt_device) && !watchdog_hw_running(&wdt->wdt_device);
}
