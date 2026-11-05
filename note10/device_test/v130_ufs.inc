/* SPDX-License-Identifier: GPL-2.0-only */
/* Same pinned Exynos UFS TU. Generic shutdown returns 0 even on internal error. */
#include <linux/v130_kernel_api.h>
static unsigned int n130_ufs_count;
static int n130_ufs_stop_device(struct device *device,void *unused)
{
    struct ufs_hba *hba;(void)unused;
    if(device->driver!=&exynos_ufs_driver.driver)return 0;
    hba=dev_get_drvdata(device);if(!hba)return -ENODEV;
    (void)ufshcd_shutdown(hba);
    if(!n130_dma_ready(device) || hba->curr_dev_pwr_mode!=UFS_POWERDOWN_PWR_MODE || !ufshcd_is_link_off(hba))return -EIO;
    n130_ufs_count++;return 0;
}
int n130_ufs_prepare(void)
{
    int error=bus_for_each_dev(&platform_bus_type,NULL,NULL,n130_ufs_stop_device);
    return error?error:(n130_ufs_count?0:-ENODEV);
}
