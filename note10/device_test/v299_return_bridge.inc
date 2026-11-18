/* Root-only RAM state; staging does not arm the watchdog or replace the worker. */
#include <linux/capability.h>
#include <linux/kobject.h>
#include <linux/sysfs.h>
#include <linux/n299_return_contract.h>
extern int n299_sec_prepare_recovery(void);
extern int n299_wdt_eligible(void);
static atomic_t n299_spent=ATOMIC_INIT(0);
static int n299_prepared;
static struct kobject *n299_kobject;
static unsigned long n299_remaining(void)
{
    unsigned long expires=READ_ONCE(n10_return_work.timer.expires);
    return time_after(expires,jiffies)?jiffies_to_msecs(expires-jiffies):0;
}
static int n299_ready(unsigned long remaining)
{
    return system_state==SYSTEM_RUNNING && n10_cycle_valid() && READ_ONCE(n154_arm_result)==0 &&
        delayed_work_pending(&n10_return_work) &&
        n299_budget(atomic_read(&n10_return_started),atomic_read(&n10_return_requested),
                    n299_wdt_eligible(),remaining,atomic_read(&n299_spent));
}
static ssize_t n299_status_show(struct kobject *kobj,struct kobj_attribute *attr,char *buf)
{
    unsigned long remaining=n299_remaining();(void)kobj;(void)attr;
    return scnprintf(buf,PAGE_SIZE,"%s %s %s %d %d %lu\n",N154_BUILD_ID,(const char *)n10_cycle,n10_boot_id,
                     n299_ready(remaining),READ_ONCE(n299_prepared),remaining);
}
static ssize_t n299_prepare_store(struct kobject *kobj,struct kobj_attribute *attr,const char *buf,size_t count)
{
    char expected[100];int result;(void)kobj;(void)attr;
    if(!capable(CAP_SYS_BOOT))return -EPERM;
    if(n299_command(expected,N154_BUILD_ID,(const char *)n10_cycle,n10_boot_id)!=99 ||
       count!=99 || memcmp(buf,expected,99) || !n299_ready(n299_remaining()))return -EINVAL;
    if(atomic_cmpxchg(&n299_spent,0,1))return -EBUSY;
    result=n299_sec_prepare_recovery();WRITE_ONCE(n299_prepared,result?2:1);
    pr_info("N299PREP id=%s boot=%s cycle=%s result=%d remaining_ms=%lu\n",N154_BUILD_ID,n10_boot_id,(const char *)n10_cycle,result,n299_remaining());
    return result?result:(ssize_t)count;
}
static struct kobj_attribute n299_status_attr=__ATTR(status,0400,n299_status_show,NULL);
static struct kobj_attribute n299_prepare_attr=__ATTR(prepare,0200,NULL,n299_prepare_store);
static struct attribute *n299_attributes[]={&n299_status_attr.attr,&n299_prepare_attr.attr,NULL};
static const struct attribute_group n299_group={.attrs=n299_attributes};
static int __init n299_interface_init(void)
{
    int result;n299_kobject=kobject_create_and_add("n299_return",kernel_kobj);
    if(!n299_kobject)return -ENOMEM;
    result=sysfs_create_group(n299_kobject,&n299_group);
    if(result){kobject_put(n299_kobject);n299_kobject=NULL;}
    return result;
}
late_initcall(n299_interface_init);
