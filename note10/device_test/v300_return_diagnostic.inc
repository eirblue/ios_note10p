/* Separate read-only attribute; existing status/prepare ABI and decision stay intact. */
#include <linux/n300_return_diagnostic.h>
extern void n300_wdt_snapshot(struct n300_wdt_fields *s);
static ssize_t n300_diagnostic_show(struct kobject *kobj,struct kobj_attribute *attr,char *buf)
{
    struct n300_wdt_fields s;struct n300_outer_fields o;u32 driver,outer;
    (void)kobj;(void)attr;
    n300_wdt_snapshot(&s);
    o.running=system_state==SYSTEM_RUNNING;o.cycle_ok=n10_cycle_valid();o.arm_result=READ_ONCE(n154_arm_result);
    o.pending=delayed_work_pending(&n10_return_work);o.armed=atomic_read(&n10_return_started);
    o.requested=atomic_read(&n10_return_requested);o.remaining=n299_remaining();o.spent=atomic_read(&n299_spent);
    driver=n300_wdt_reasons(&s);outer=n300_outer_reasons(&o);
    return scnprintf(buf,PAGE_SIZE,
        "N300DIAG id=%s cycle=%s boot=%s ready=%d driver_mask=%08x outer_mask=%08x "
        "present=%u soft=%u nowayout=%u cluster=%u variant=%u route=%u rate=%u gate=%u freq=%llu "
        "multi=%u device_id=%u timeout=%u maxhm=%u active=%u hw=%u "
        "running=%u cycle_ok=%u arm_result=%d pending=%u armed=%u requested=%u remaining_ms=%lu spent=%u\n",
        N154_BUILD_ID,(const char *)n10_cycle,n10_boot_id,n299_ready(o.remaining),driver,outer,
        s.present,s.soft_noboot,s.nowayout,s.cluster,s.variant,s.route_func,s.rate_clock,s.gate_clock,
        (unsigned long long)s.freq,s.multistage,s.device_id,s.timeout,s.max_heartbeat,s.active,s.hw_running,
        o.running,o.cycle_ok,o.arm_result,o.pending,o.armed,o.requested,o.remaining,o.spent);
}
static struct kobj_attribute n300_diagnostic_attr=__ATTR(diagnostic,0400,n300_diagnostic_show,NULL);
static int __init n300_diagnostic_init(void)
{
    if(!n299_kobject)return -ENODEV;
    return sysfs_create_file(n299_kobject,&n300_diagnostic_attr.attr);
}
late_initcall(n300_diagnostic_init);
