/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in arm64/mm/init.c, at the existing source-pinned early phase. */
#include <linux/capability.h>
#include <linux/device.h>
#include <linux/delay.h>
#include <linux/init.h>
#include <linux/kexec.h>
#include <linux/kobject.h>
#include <linux/memblock.h>
#include <linux/mm.h>
#include <linux/platform_device.h>
#include <linux/random.h>
#include <linux/reboot.h>
#include <linux/sched.h>
#include <linux/sysfs.h>
#include <linux/workqueue.h>
#include <linux/legacy_kexec_core.h>
#include <linux/legacy_kexec_return.h>
#include <linux/note10_legacy_kexec_build.h>
#include <linux/v130_kernel_api.h>
#include <asm/cputype.h>
#include <asm/sysreg.h>
#include <asm/smp_plat.h>
#include <asm/system_misc.h>
static struct n130_wire n130_destination,n130_armed;
static struct n130_platform n130_platform;
static int n130_reserved,n130_arm_state;
enum n130_return_phase { N130_IDLE=0,N130_RECOVERY=1,N130_ARMING=2,N130_HARDWARE=3,N130_TIMEOUT_PENDING=4 };
static int n130_return_owner;
static const struct kimage *n130_pending_image;
static struct {struct device *device;int result;} n130_dma[128];
static unsigned int n130_dma_count;
static void n130_deadline_fn(struct work_struct *work)
{
    (void)work;pr_emerg("N10XNU130 Linux preparation deadline; recovery, no transfer\n");
    kernel_restart("recovery");
}
static DECLARE_DELAYED_WORK(n130_deadline,n130_deadline_fn);
int n130_recovery_claim(void)
{
    int owner,target;
    for(;;){
        owner=READ_ONCE(n130_return_owner);
        if(owner==N130_IDLE)target=N130_RECOVERY;
        else if(owner==N130_ARMING)target=N130_TIMEOUT_PENDING;
        else return -EBUSY;
        if(cmpxchg(&n130_return_owner,owner,target)==owner)break;
    }
    /* A deadline during bounded HW arming is retained, never a competing restart. */
    if(target==N130_TIMEOUT_PENDING)return -EBUSY;
    cancel_delayed_work(&n130_deadline);return 0;
}
static int n130_el1(void){return read_sysreg(CurrentEL)==4;}
static int n130_extent(void *unused,unsigned int index,n130_u64 *low,n130_u64 *high)
{
    u64 cursor;phys_addr_t start,end;unsigned int current_index=0;(void)unused;
    for_each_free_mem_range_reverse(cursor,NUMA_NO_NODE,MEMBLOCK_NONE,&start,&end,NULL){
        if(current_index++==index){*low=start;*high=end;return 1;}
    }
    return 0;
}
static int n130_available(void *unused,n130_u64 base,n130_u64 bytes)
{(void)unused;return memblock_is_region_memory(base,bytes) && !memblock_is_region_reserved(base,bytes);}
static int n130_reservation(void *unused,n130_u64 base,n130_u64 bytes)
{(void)unused;return memblock_reserve(base,bytes);}
static void __init n10_early_kexec_destination(void)
{
    static const struct n130_reserve_ops ops={n130_extent,n130_available,n130_reservation};
    n130_u64 base=0;
    if(!n130_reserve(&ops,NULL,&base)){n130_destination.base=base;n130_destination.size=N130_MEMORY;n130_reserved=1;}
}
int n130_dma_record(struct device *device,int result)
{
    unsigned int i;
    if(READ_ONCE(n130_arm_state)!=2)return 0;
    for(i=0;i<n130_dma_count;i++)if(n130_dma[i].device==device){n130_dma[i].result=result;return result;}
    if(n130_dma_count>=ARRAY_SIZE(n130_dma))return -ENOSPC;
    n130_dma[n130_dma_count].device=device;n130_dma[n130_dma_count++].result=result;return result;
}
int n130_dma_ready(struct device *device)
{
    unsigned int i;for(i=0;i<n130_dma_count;i++)if(n130_dma[i].device==device)return n130_dma[i].result==0;
    return 0;
}
static ssize_t n130_read(struct file *file,struct kobject *object,struct bin_attribute *attr,
                        char *buffer,loff_t offset,size_t count)
{
    const void *data=attr->private;size_t bytes=attr->size;(void)file;(void)object;
    if(offset<0 || offset>=bytes)return 0;
    count=min_t(size_t,count,bytes-(size_t)offset);memcpy(buffer,(const char *)data+offset,count);return count;
}
static ssize_t n130_arm(struct file *file,struct kobject *object,struct bin_attribute *attr,
                       char *buffer,loff_t offset,size_t count)
{
    struct n130_wire request;u32 status;(void)file;(void)object;(void)attr;
    if(offset || count!=sizeof(request) || !capable(CAP_SYS_BOOT) || task_pid_nr(current)!=1)return -EPERM;
    memcpy(&request,buffer,sizeof(request));status=request.status;request.status=1;
    if(n130_parcel(&request,N10_KEXEC_BUILD_ID) || request.base!=n130_destination.base ||
       memcmp(request.cookie,n130_destination.cookie,16) || memcmp(request.build,n130_destination.build,32))return -EINVAL;
    if(status==0){if(cmpxchg(&n130_arm_state,1,4)!=1)return -EBUSY;return count;}
    if(status!=1 || !n130_el1() || cmpxchg(&n130_arm_state,0,1)!=0)return -EPERM;
    if(n10_sec_stage_kexec_recovery()){WRITE_ONCE(n130_arm_state,4);return -EIO;}
    n130_armed=request;return count;
}
static struct bin_attribute n130_destination_attr={.attr={.name="destination",.mode=0400},.size=224,.read=n130_read,.private=&n130_destination};
static struct bin_attribute n130_platform_attr={.attr={.name="platform",.mode=0400},.size=128,.read=n130_read,.private=&n130_platform};
static struct bin_attribute n130_arm_attr={.attr={.name="arm",.mode=0200},.size=224,.write=n130_arm};
static int __init n130_publish(void)
{
    unsigned long first,i;struct kobject *object;int result;
    /* Linux deadline covers early PID1/mount/file/crypto/prepare failures only. */
    schedule_delayed_work(&n130_deadline,90*HZ);
    if(!n130_reserved || PAGE_SHIFT!=12 || !n130_el1())return 0;
    first=PHYS_PFN(n130_destination.base);
    for(i=0;i<N130_MEMORY/PAGE_SIZE;i++)if(!pfn_valid(first+i) || !PageReserved(pfn_to_page(first+i)))return 0;
    memcpy(n130_destination.magic,"N10XNU2",8);n130_destination.schema=2;n130_destination.bytes=224;
    memcpy(n130_destination.build,N10_KEXEC_BUILD_ID,32);get_random_bytes(n130_destination.cookie,16);
    n130_destination.generation=1;n130_destination.status=1;n130_destination.page_shift=PAGE_SHIFT;
    if(n130_descriptor(&n130_destination,N10_KEXEC_BUILD_ID))return 0;
    memcpy(n130_platform.magic,"N10PLAT1",8);n130_platform.schema=1;n130_platform.bytes=128;
    n130_platform.mpidr=cpu_logical_map(0)&MPIDR_HWID_BITMASK;
    result=n130_gic_platform(&n130_platform);if(!result)result=n130_timer_platform(&n130_platform);
    if(result)return 0;
    n130_platform.status=1;
    object=kobject_create_and_add("note10_xnu",kernel_kobj);if(!object)return -ENOMEM;
    result=sysfs_create_bin_file(object,&n130_destination_attr);
    if(!result)result=sysfs_create_bin_file(object,&n130_platform_attr);
    if(!result)result=sysfs_create_bin_file(object,&n130_arm_attr);
    if(result){sysfs_remove_bin_file(object,&n130_destination_attr);sysfs_remove_bin_file(object,&n130_platform_attr);kobject_put(object);return result;}
    pr_info("N10XNU130 id=%s fresh_owned32M platform_ready=1 xnu_pending=1\n",N10_KEXEC_BUILD_ID);return 0;
}
late_initcall(n130_publish);
int n10_kexec_check_image(const struct kimage *image)
{
    int state=READ_ONCE(n130_arm_state);
    if((state!=1 && state!=2) || !n130_el1() || n130_parcel(&n130_armed,N10_KEXEC_BUILD_ID) ||
       !image || image->type!=KEXEC_TYPE_DEFAULT || image->nr_segments!=1 ||
       image->start!=n130_armed.base+n130_armed.adapter_offset || image->segment[0].mem!=n130_armed.base ||
       image->segment[0].memsz!=N130_MEMORY || image->segment[0].bufsz!=n130_armed.top_offset)return -EPERM;
    return 0;
}
int n130_before_shutdown(const struct kimage *image)
{
    int result=n10_kexec_check_image(image);
    if(!result && READ_ONCE(n130_return_owner)!=N130_IDLE)result=-EBUSY;
    if(!result)result=n10_sec_stage_kexec_recovery();
    if(result)return result;
    /* Marker precedes blocking notifiers/freezer; Linux90s deadline still owns them. */
    WRITE_ONCE(n130_pending_image,image);return 0;
}
int n130_before_device_shutdown(void)
{
    const struct kimage *image=READ_ONCE(n130_pending_image);
    struct n10_wdt_witness witness={0};int result;
    if(!image)return 0; /* Ordinary recovery/restart, not a pending XNU transfer. */
    result=n10_kexec_check_image(image);if(result)return result;
    if(cmpxchg(&n130_return_owner,N130_IDLE,N130_ARMING)!=N130_IDLE)return -EBUSY;
    if(READ_ONCE(n130_return_owner)!=N130_ARMING)return -ETIMEDOUT;
    result=n10_sec_stage_kexec_recovery();
    if(!result && READ_ONCE(n130_return_owner)!=N130_ARMING)result=-ETIMEDOUT;
    if(!result)result=n10_wdt_stage_kexec_return(&witness);
    if(!result && READ_ONCE(n130_return_owner)!=N130_ARMING)result=-ETIMEDOUT;
    if(!result)result=n10_watchdog_qualified(&witness);
    if(result)return result;
    /* Same atomic word commits qualification or observes a racing pending timeout. */
    if(cmpxchg(&n130_return_owner,N130_ARMING,N130_HARDWARE)!=N130_ARMING)return -ETIMEDOUT;
    if(cmpxchg(&n130_arm_state,1,2)!=1)return -EBUSY;
    cancel_delayed_work_sync(&n130_deadline);
    /* No DMA/PM/IRQ mutation before qualified HW has taken the deadline. */
    return n130_dmaengine_prepare();
}
void n130_terminal_recovery(void)
{
    WRITE_ONCE(n130_arm_state,4);WRITE_ONCE(n130_pending_image,NULL);
    xchg(&n130_return_owner,N130_RECOVERY);
    if(n10_sec_stage_kexec_recovery())pr_emerg("N10XNU130 recovery marker readback failed; no transfer\n");
    machine_restart("recovery");
    BUG();
}
int n130_after_shutdown(void)
{
    int result=n130_usb_prepare();
    if(!result)result=n130_ufs_prepare();
    if(!result)result=n130_iommu_prepare();
    return result;
}
int n10_kexec_final_return(const struct kimage *image)
{
    struct n10_wdt_witness witness={0};int result;
    result=n10_kexec_check_image(image);
    if(!result && (READ_ONCE(n130_arm_state)!=2 || READ_ONCE(n130_return_owner)!=N130_HARDWARE || num_online_cpus()!=1 ||
       (read_sysreg(mpidr_el1)&MPIDR_HWID_BITMASK)!=n130_platform.mpidr))result=-EPERM;
    if(!result)result=n130_dmaengine_final();
    if(!result)result=n130_usb_final();
    if(!result)result=n130_iommu_final();
    if(!result)result=n130_timer_final();
    if(!result)result=n130_gic_final();
    if(!result)result=n10_sec_stage_kexec_recovery();
    if(!result)result=n10_wdt_stage_kexec_return(&witness);
    if(!result)result=n10_watchdog_qualified(&witness);
    if(!result && cmpxchg(&n130_arm_state,2,3)!=2)result=-EBUSY;
    if(result){WRITE_ONCE(n130_arm_state,4);return result;}
    pr_emerg("N10XNU130 id=%s final_qualified=1 EL1_preserved=1 actual_XNU_pending=1\n",N10_KEXEC_BUILD_ID);return 0;
}
