/* SPDX-License-Identifier: GPL-2.0-only */
/* Included before arm64_memblock_init; early reservation, persistent descriptor. */
#include <linux/init.h>
#include <linux/memblock.h>
#include <linux/mm.h>
#include <linux/random.h>
#include <linux/kobject.h>
#include <linux/sysfs.h>
#include <linux/string.h>
#include <linux/kernel.h>
#include <linux/capability.h>
#include <linux/legacy_kexec_return.h>
#include <linux/note10_legacy_kexec_build.h>
static struct n10_destination n10_kexec_dest;
static int n10_kexec_reserved, n10_kexec_arm_state;
static n10_u64 __init n10_find(void *p,n10_u64 lo,n10_u64 hi,n10_u64 size,n10_u64 align)
{(void)p;return memblock_find_in_range(lo,hi,size,align);}
static int __init n10_memory(void *p,n10_u64 base,n10_u64 size)
{(void)p;return memblock_is_region_memory(base,size);}
static int __init n10_reserved(void *p,n10_u64 base,n10_u64 size)
{(void)p;return memblock_is_region_reserved(base,size);}
static int __init n10_reserve(void *p,n10_u64 base,n10_u64 size)
{(void)p;return memblock_reserve(base,size);}
static const struct n10_reserve_ops n10_reserve_callbacks __initconst={n10_find,n10_memory,n10_reserved,n10_reserve};
static void __init n10_early_kexec_destination(void)
{
    n10_u64 base=0;
    if(n10_reserve_destination(&n10_reserve_callbacks,NULL,&base))return;
    n10_kexec_dest.base=base;n10_kexec_dest.size=N10_KEXEC_BYTES;n10_kexec_reserved=1;
}
static ssize_t n10_destination_read(struct file *file,struct kobject *object,struct bin_attribute *attr,
                                   char *buffer,loff_t offset,size_t count)
{
    (void)file;(void)object;(void)attr;
    if(offset<0)return -EINVAL;
    if(offset>=(loff_t)sizeof(n10_kexec_dest))return 0;
    count=min_t(size_t,count,sizeof(n10_kexec_dest)-(size_t)offset);
    memcpy(buffer,(const u8 *)&n10_kexec_dest+offset,count);return count;
}
static ssize_t n10_arm_write(struct file *file,struct kobject *object,struct bin_attribute *attr,
                            char *buffer,loff_t offset,size_t count)
{
    struct n10_destination input;u32 requested;
    (void)file;(void)object;(void)attr;
    if(offset || count!=sizeof(input) || !capable(CAP_SYS_BOOT))return -EINVAL;
    memcpy(&input,buffer,sizeof(input));requested=input.status;input.status=1;
    if(n10_destination_valid(&n10_kexec_dest,N10_KEXEC_BUILD_ID) ||
       memcmp(&input,&n10_kexec_dest,sizeof(input)))return -EINVAL;
    if(requested==1){
        if(cmpxchg(&n10_kexec_arm_state,0,1)!=0)return -EBUSY;
        /* Stage before device_shutdown can arm its existing watchdog. Recheck
         * at the final boundary; any failed attempt remains consumed. */
        if(n10_sec_stage_kexec_recovery()){WRITE_ONCE(n10_kexec_arm_state,3);return -EIO;}
    }
    else if(requested==0){if(cmpxchg(&n10_kexec_arm_state,1,3)!=1)return -EBUSY;}
    else return -EINVAL;
    return count;
}
static struct bin_attribute n10_destination_attr={.attr={.name="destination",.mode=0400},.size=128,.read=n10_destination_read};
static struct bin_attribute n10_arm_attr={.attr={.name="arm",.mode=0200},.size=128,.write=n10_arm_write};
static int __init n10_publish_destination(void)
{
    unsigned long i,first;struct kobject *object;int result;
    if(!n10_kexec_reserved || PAGE_SHIFT!=12)return 0;
    memcpy(n10_kexec_dest.magic,"N10KRES1",8);n10_kexec_dest.schema=1;n10_kexec_dest.bytes=128;
    memcpy(n10_kexec_dest.build,N10_KEXEC_BUILD_ID,32);n10_kexec_dest.page_shift=PAGE_SHIFT;
    n10_kexec_dest.generation=1;first=PHYS_PFN(n10_kexec_dest.base);
    for(i=0;i<(N10_KEXEC_BYTES>>PAGE_SHIFT);i++){
        if(!pfn_valid(first+i))continue;
        ++n10_kexec_dest.valid_pages;
        if(PageReserved(pfn_to_page(first+i)))++n10_kexec_dest.reserved_pages;
    }
    /* Fresh correlation cookie only; no entropy/authentication claim. */
    get_random_bytes(n10_kexec_dest.cookie,sizeof(n10_kexec_dest.cookie));
    n10_kexec_dest.status=1;
    if(n10_destination_valid(&n10_kexec_dest,N10_KEXEC_BUILD_ID)){n10_kexec_dest.status=0;return 0;}
    object=kobject_create_and_add("note10_kexec",kernel_kobj);if(!object)return -ENOMEM;
    result=sysfs_create_bin_file(object,&n10_destination_attr);
    if(!result)result=sysfs_create_bin_file(object,&n10_arm_attr);
    if(result){sysfs_remove_bin_file(object,&n10_destination_attr);kobject_put(object);return result;}
    pr_info("N10KRES1 id=%s bytes=33554432 generation=1 ready=1 xnu=0\n",N10_KEXEC_BUILD_ID);
    return 0;
}
late_initcall(n10_publish_destination);
int n10_kexec_check_image(const struct kimage *image)
{
    if(n10_kexec_arm_state!=1 || n10_destination_valid(&n10_kexec_dest,N10_KEXEC_BUILD_ID) ||
       !image || image->type!=KEXEC_TYPE_DEFAULT || image->nr_segments!=1 ||
       image->start!=n10_kexec_dest.base || image->segment[0].mem!=n10_kexec_dest.base ||
       image->segment[0].memsz!=N10_KEXEC_BYTES || image->segment[0].bufsz!=N10_KEXEC_ALIGN)return -EPERM;
    return 0;
}
int n10_kexec_final_return(const struct kimage *image)
{
    struct n10_wdt_witness witness={0};int result;
    result=n10_kexec_check_image(image);
    if(!result)result=n10_sec_stage_kexec_recovery();
    if(!result)result=n10_wdt_stage_kexec_return(&witness);
    if(!result)result=n10_watchdog_qualified(&witness);
    if(!result && cmpxchg(&n10_kexec_arm_state,1,2)!=1)result=-EBUSY;
    if(result){WRITE_ONCE(n10_kexec_arm_state,3);return result;}
    pr_emerg("N10KRET1 id=%s marker_readback=1 wdt_qualified=1 first=%u last=%u timeout=%u physical_park_pending=1 xnu=0\n",
             N10_KEXEC_BUILD_ID,witness.first_count,witness.last_count,witness.effective_timeout);
    return 0;
}
