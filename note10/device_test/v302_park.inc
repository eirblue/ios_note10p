/* One-way all-online stop_machine experiment; no XNU/MMU/power/clock/driver shutdown. */
#include <linux/stop_machine.h>
#include <linux/cpu.h>
#include <linux/printk.h>
#include <asm/barrier.h>
#include <asm/processor.h>
#include <linux/n302_park_contract.h>
static atomic_t n302_attempted=ATOMIC_INIT(0);
static atomic_t n302_committed=ATOMIC_INIT(0);
void __noreturn n302_spin(void);
int n302_cpu0(void *unused);
ssize_t n302_park_write(struct kobject *kobj,struct kobj_attribute *attr,const char *buf,size_t count);
static int n302_ready(void)
{
    struct n300_wdt_fields w;struct n302_gate g;
    n300_wdt_snapshot(&w);g.running=system_state==SYSTEM_RUNNING;
    g.prepared=READ_ONCE(n299_prepared);g.spent=atomic_read(&n299_spent);
    g.armed=atomic_read(&n10_return_started);g.requested=atomic_read(&n10_return_requested);
    g.pending=delayed_work_pending(&n10_return_work);g.cpu0_online=cpu_online(0);g.remaining=n299_remaining();
    return n10_cycle_valid() && READ_ONCE(n154_arm_result)==0 && n302_gate_ready(&g,&w);
}
void __noreturn noinline n302_spin(void)
{
    for(;;)cpu_relax();
}
int noinline n302_cpu0(void *unused)
{
    unsigned int cpu=raw_smp_processor_id(),count=num_online_cpus(),sequence;
    u64 online=0;char frame[256];int length,index;(void)unused;
    /* stop_machine holds cpus_read_lock; RUN follows every disable-IRQ ACK. */
    for_each_online_cpu(index){if(index>=64)return -E2BIG;online|=1ULL<<index;}
    if(!n302_online_ok(online,count,cpu,irqs_disabled()) || !n302_ready())return -EINVAL;
    if(atomic_cmpxchg(&n10_return_requested,0,1))return -EBUSY;
    atomic_set(&n302_committed,1);
    for(sequence=0;sequence<16;++sequence){
        length=scnprintf(frame,sizeof(frame),"id=%s boot=%s cycle=%s seq=%u cpu=%u irq_off=1 online=%016llx count=%u timeout=10 commit=1",
                         N154_BUILD_ID,n10_boot_id,(const char *)n10_cycle,sequence,cpu,(unsigned long long)online,count);
        /* No console lock: log_store synchronously updates the existing NC snapshot RAM. */
        printk_deferred(KERN_EMERG "N302QUIESCE %s checksum=%08x\n",frame,n10_frame_checksum(frame,length));
    }
    dsb(sy);
    n302_spin();
}
ssize_t n302_park_write(struct kobject *kobj,struct kobj_attribute *attr,const char *buf,size_t count)
{
    char expected[100];(void)kobj;(void)attr;
    if(!capable(CAP_SYS_BOOT))return -EPERM;
    if(n299_command(expected,N154_BUILD_ID,(const char *)n10_cycle,n10_boot_id)!=99 || count!=99 || memcmp(buf,expected,99))return -EINVAL;
    if(atomic_cmpxchg(&n302_attempted,0,1))return -EBUSY;
    if(!n302_ready())return -EINVAL;
    /* Standard API may block; already armed hardware bounds stalls, not a software guarantee. */
    return stop_machine(n302_cpu0,NULL,cpumask_of(0));
}
static struct kobj_attribute n302_park_attr=__ATTR(park,0200,NULL,n302_park_write);
static int __init n302_park_init(void)
{
    if(!n299_kobject)return -ENODEV;
    return sysfs_create_file(n299_kobject,&n302_park_attr.attr);
}
late_initcall(n302_park_init);
