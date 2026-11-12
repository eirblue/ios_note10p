/* SPDX-License-Identifier: GPL-2.0-only */
/* Included only at the exact early ARM64 memblock source boundary. */
#include <crypto/hash.h>
#include <linux/capability.h>
#include <linux/init.h>
#include <linux/kobject.h>
#include <linux/memblock.h>
#include <linux/mm.h>
#include <linux/mutex.h>
#include <linux/random.h>
#include <linux/sched.h>
#include <linux/sysfs.h>
#include <linux/string.h>
#include "native_prepare_core.h"
static struct n210_destination n210_destination;
static struct n210_receipt n210_result;
static unsigned int n210_reserved,n210_spent;
static DEFINE_MUTEX(n210_lock);
static void __init n210_early_reserve(void)
{
    u64 cursor;phys_addr_t low,high,base;unsigned int count=0;
    for_each_free_mem_range_reverse(cursor,NUMA_NO_NODE,MEMBLOCK_NONE,&low,&high,NULL){
        if(++count>4096)break;
        if(high>N209_ADDRESS_LIMIT)high=N209_ADDRESS_LIMIT;
        if(low<N209_ADDRESS_MIN)low=N209_ADDRESS_MIN;
        if(high<=low||high<N209_DESTINATION_BYTES+N210_RESIDUE)continue;
        base=((high-N209_DESTINATION_BYTES-N210_RESIDUE)&~(N209_DESTINATION_BYTES-1))+N210_RESIDUE;
        if(base<low||base>N209_ADDRESS_LIMIT-N209_DESTINATION_BYTES||
           !memblock_is_region_memory(base,N209_DESTINATION_BYTES)||memblock_is_region_reserved(base,N209_DESTINATION_BYTES))continue;
        if(memblock_reserve(base,N209_DESTINATION_BYTES))return;
        n210_destination.region.base=base;n210_destination.region.size=N209_DESTINATION_BYTES;n210_reserved=1;return;
    }
}
static int n210_pages(void)
{
    unsigned long i,first=PHYS_PFN(n210_destination.region.base);
    if(!n210_reserved||PAGE_SHIFT!=12)return 0;
    for(i=0;i<N209_DESTINATION_BYTES/PAGE_SIZE;i++)if(!pfn_valid(first+i)||!PageReserved(pfn_to_page(first+i)))return 0;
    return 1;
}
static ssize_t n210_read(struct file *file,struct kobject *object,struct bin_attribute *attr,char *buffer,loff_t offset,size_t count)
{
    (void)file;(void)object;
    if(offset<0||offset>=attr->size)return 0;
    if(attr->private==&n210_result&&!READ_ONCE(n210_result.status))return -EAGAIN;
    count=min_t(size_t,count,attr->size-(size_t)offset);memcpy(buffer,(const char *)attr->private+offset,count);return count;
}
static ssize_t n210_write(struct file *file,struct kobject *object,struct bin_attribute *attr,char *buffer,loff_t offset,size_t count)
{
    struct n210_request request;struct n210_context context;struct crypto_shash *tfm;
    n209_u8 hash[32];int error;(void)file;(void)object;(void)attr;
    if(offset||count!=sizeof(request)||task_pid_nr(current)!=1||!capable(CAP_SYS_BOOT))return -EPERM;
    if(!mutex_trylock(&n210_lock))return -EBUSY;
    if(n210_spent){error=-EALREADY;goto out;}
    memcpy(&request,buffer,sizeof(request));memset(&context,0,sizeof(context));
    error=n210_linux_context(&context);
    context.page_reserved=n210_pages();context.pid1=task_pid_nr(current)==1;context.cap_sys_boot=capable(CAP_SYS_BOOT);
    if(error){n210_spent=1;goto out;}
    tfm=crypto_alloc_shash("sha256",0,0);
    if(IS_ERR(tfm)){error=PTR_ERR(tfm);n210_spent=1;goto out;}
    {
        SHASH_DESC_ON_STACK(desc,tfm);desc->tfm=tfm;desc->flags=0;
        error=crypto_shash_digest(desc,request.payload,sizeof(request.payload),hash);
    }
    crypto_free_shash(tfm);
    if(error){n210_spent=1;goto out;}
    error=n210_prepare_once(&request,&n210_destination,&context,hash,&n210_spent,&n210_result);
    if(!error)pr_info("N210PREP id=%.32s boot=%.32s cycle=%.32s reserved32M=1 descriptor_bound=1 native_source=0 qualified_XNU_return=0\n",context.build,context.boot,context.cycle);
 out:
    mutex_unlock(&n210_lock);return error?error:(ssize_t)count;
}
static struct bin_attribute n210_dest_attr={.attr={.name="destination",.mode=0400},.size=96,.read=n210_read,.private=&n210_destination};
static struct bin_attribute n210_prepare_attr={.attr={.name="prepare",.mode=0200},.size=480,.write=n210_write};
static struct bin_attribute n210_result_attr={.attr={.name="result",.mode=0400},.size=192,.read=n210_read,.private=&n210_result};
static int __init n210_publish(void)
{
    struct n210_context context;struct kobject *object;int error;
    if(!n210_pages())return 0;
    memset(&context,0,sizeof(context));
    /* Identity exists before PID1; actual return-arm is checked on the write. */
    (void)n210_linux_context(&context);
    memcpy(n210_destination.magic,"N210DST1",8);n210_destination.schema=1;n210_destination.bytes=96;
    n210_destination.region.generation=1;n210_destination.region.page_shift=PAGE_SHIFT;n210_destination.region.status=1;
    memcpy(n210_destination.region.build,context.build,32);get_random_bytes(n210_destination.region.cookie,16);
    if(!memchr_inv(n210_destination.region.cookie,0,16))return 0;
    object=kobject_create_and_add("note10_native_prepare",kernel_kobj);if(!object)return -ENOMEM;
    error=sysfs_create_bin_file(object,&n210_dest_attr);
    if(!error)error=sysfs_create_bin_file(object,&n210_prepare_attr);
    if(!error)error=sysfs_create_bin_file(object,&n210_result_attr);
    if(error){sysfs_remove_bin_file(object,&n210_dest_attr);sysfs_remove_bin_file(object,&n210_prepare_attr);sysfs_remove_bin_file(object,&n210_result_attr);kobject_put(object);}
    return error;
}
late_initcall(n210_publish);
