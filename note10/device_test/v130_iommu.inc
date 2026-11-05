/* SPDX-License-Identifier: GPL-2.0-only */
/* Same pinned exynos-iommu.c TU: inspect its actual probed owner list. */
#include <linux/v130_kernel_api.h>
static int n130_iommu_terminal;
int n130_iommu_prepare(void)
{
    struct exynos_iommu_owner *owner;struct sysmmu_list_data *item;
    unsigned long flags;int error=0;
    for(owner=sysmmu_owner_list;owner;owner=owner->next){
        spin_lock_irqsave(&owner->lock,flags);
        list_for_each_entry(item,&owner->sysmmu_list,node){
            struct sysmmu_drvdata *data=dev_get_drvdata(item->sysmmu);
            if(!data || ((is_sysmmu_active(data) || is_runtime_active_or_enabled(data)) && !n130_dma_ready(owner->master))){error=-EBUSY;break;}
        }
        spin_unlock_irqrestore(&owner->lock,flags);
        if(error)return error;
    }
    /* No global disable: stopped masters cannot DMA; preserved domains remain owned. */
    WRITE_ONCE(n130_iommu_terminal,1);return 0;
}
int n130_iommu_final(void)
{
    /* No owner-list/spinlock/PM operation after nonboot CPU stop. */
    return READ_ONCE(n130_iommu_terminal)?0:-EBUSY;
}
