/* SPDX-License-Identifier: GPL-2.0-only */
/* Same pinned arm_arch_timer.c TU: use its real registered timer and accessors. */
#include <linux/of_irq.h>
#include <linux/irq.h>
#include <linux/v130_kernel_api.h>
static int n130_timer_probed;
int n130_timer_platform(struct n130_platform *platform)
{
    struct device_node *node;struct of_phandle_args irq;struct irq_data *data;u32 rate;int error;
    node=of_find_compatible_node(NULL,NULL,"arm,armv8-timer");
    if(!node || !of_device_is_available(node))return -ENODEV;
    error=of_property_read_u32(node,"clock-frequency",&rate);
    if(!error)error=of_irq_parse_one(node,ARCH_TIMER_PHYS_NONSECURE_PPI,&irq);
    of_node_put(node);if(error)return error;
    if(irq.args_count!=3 || irq.args[0]!=1 || irq.args[1]>=16){of_node_put(irq.np);return -EINVAL;}
    data=irq_get_irq_data(arch_timer_ppi[ARCH_TIMER_PHYS_NONSECURE_PPI]);
    if(!data || irqd_to_hwirq(data)!=16+irq.args[1] || 16+irq.args[1]!=30 ||
       !arch_timer_evt || rate!=26000000 || rate!=arch_timer_rate || rate!=read_sysreg(cntfrq_el0))error=-EINVAL;
    else{platform->frequency=rate;platform->timer_intid=16+irq.args[1];n130_timer_probed=1;}
    of_node_put(irq.np);return error;
}
int n130_timer_final(void)
{
    struct clock_event_device *event;unsigned int control;
    if(!READ_ONCE(n130_timer_probed) || !arch_timer_evt || read_sysreg(cntfrq_el0)!=26000000)return -ENODEV;
    event=this_cpu_ptr(arch_timer_evt);
    if(arch_timer_shutdown_phys(event) || arch_timer_shutdown_virt(event))return -EIO;
    if((arch_timer_reg_read(ARCH_TIMER_PHYS_ACCESS,ARCH_TIMER_REG_CTRL,event)&ARCH_TIMER_CTRL_ENABLE) ||
       (arch_timer_reg_read(ARCH_TIMER_VIRT_ACCESS,ARCH_TIMER_REG_CTRL,event)&ARCH_TIMER_CTRL_ENABLE))return -EIO;
    control=arch_timer_get_cntkctl();
    control&=~(ARCH_TIMER_EVT_TRIGGER_MASK|ARCH_TIMER_VIRT_EVT_EN);
    arch_timer_set_cntkctl(control);isb();
    return arch_timer_get_cntkctl()&ARCH_TIMER_EVT_TRIGGER_MASK?-EIO:0;
}
