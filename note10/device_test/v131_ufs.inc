/* SPDX-License-Identifier: GPL-2.0-only */
/* Same pinned Exynos UFS TU. Forced public shutdown return0 is never evidence. */
#include <linux/v130_kernel_api.h>
static unsigned int n131_ufs_count;
static int n131_ufs_stop_device(struct device *device,void *unused)
{
    struct ufs_hba *hba;int error;(void)unused;
    if(device->driver!=&exynos_ufs_driver.driver)return 0;
    hba=dev_get_drvdata(device);
    if(!hba || hba->dev!=device){error=-ENODEV;goto refused;}
    /* Invalidate any first-shutdown result before the explicit terminal proof. */
    error=n130_dma_record(device,-EINPROGRESS);
    if(error!=-EINPROGRESS){if(!error)error=-EPERM;goto refused;}
    (void)ufshcd_shutdown(hba);
    /* Shared native out label records its actual errno, including early goto out. */
    error=n131_dma_status(device);
    if(!error && (hba->curr_dev_pwr_mode!=UFS_POWERDOWN_PWR_MODE || !ufshcd_is_link_off(hba)))error=-EIO;
    if(error)goto refused;
    n131_ufs_count++;return 0;
refused:
    n131_gate_refused("ufs-terminal",error,device);return error;
}
int n130_ufs_prepare(void)
{
    int error=bus_for_each_dev(&platform_bus_type,NULL,NULL,n131_ufs_stop_device);
    if(!error && !n131_ufs_count){error=-ENODEV;n131_gate_refused("ufs-provider",error,NULL);}
    return error;
}
