/* SPDX-License-Identifier: GPL-2.0-only */
/* Same pinned native owner list. Inactive translation is not DMA-master proof. */
#include <linux/v130_kernel_api.h>
#include <linux/note10_legacy_kexec_build.h>
static int n131_iommu_terminal;
int n130_iommu_prepare(void)
{
    struct exynos_iommu_owner *owner;struct sysmmu_list_data *item;
    struct device *failed_master=NULL,*failed_sysmmu=NULL;
    unsigned long flags;int error=0,active=0,runtime=0;
    WRITE_ONCE(n131_iommu_terminal,0);
    for(owner=sysmmu_owner_list;owner;owner=owner->next){
        active=runtime=0;failed_sysmmu=NULL;
        spin_lock_irqsave(&owner->lock,flags);
        if(!owner->master){error=-ENODEV;goto owner_done;}
        list_for_each_entry(item,&owner->sysmmu_list,node){
            struct sysmmu_drvdata *data;
            active=runtime=0;
            if(!item->sysmmu){error=-ENODEV;break;}
            data=dev_get_drvdata(item->sysmmu);
            if(!data){error=-ENODEV;failed_sysmmu=item->sysmmu;break;}
            /* Native enable/control take owner then controller in this order. */
            spin_lock(&data->lock);
            active=is_sysmmu_active(data);
            runtime=is_runtime_active_or_enabled(data);
            spin_unlock(&data->lock);
            /* The native conjunction describes register accessibility only.
             * Every master, including inactive/suspended ones, needs a proof. */
            error=n131_dma_status(owner->master);
            if(error){failed_sysmmu=item->sysmmu;break;}
        }
        if(!error && list_empty(&owner->sysmmu_list))error=-ENODEV;
owner_done:
        failed_master=owner->master;
        spin_unlock_irqrestore(&owner->lock,flags);
        if(error){
            n131_gate_refused("iommu-owner",error,failed_master);
            pr_emerg("N10XNU131 id=%s iommu controller=%.64s active=%d runtime=%d effective=%d\n",
                N10_KEXEC_BUILD_ID,failed_sysmmu?dev_name(failed_sysmmu):"none",active,runtime,active && runtime);
            return error;
        }
    }
    /* No disable, MMIO, owner-list mutation, or PM operation. */
    WRITE_ONCE(n131_iommu_terminal,1);return 0;
}
int n130_iommu_final(void)
{return READ_ONCE(n131_iommu_terminal)?0:-EBUSY;}
