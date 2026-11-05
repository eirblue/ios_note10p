/* SPDX-License-Identifier: GPL-2.0-only */
/* Same pinned irq-gic.c TU. No caller-supplied register bases. */
#include <linux/of_address.h>
#include <linux/v130_kernel_api.h>
static int n130_gic_probed;
int n130_gic_platform(struct n130_platform *platform)
{
    struct resource distributor,cpu;struct gic_chip_data *gic=&gic_data[0];
    if(!n130_gic_node || !gic->domain || gic->gic_irqs<32 || gic->gic_irqs>1020 ||
       of_address_to_resource(n130_gic_node,0,&distributor) || of_address_to_resource(n130_gic_node,1,&cpu))return -ENODEV;
    if(!gic_data_dist_base(gic) || !gic_data_cpu_base(gic))return -ENODEV;
    platform->distributor=distributor.start;platform->distributor_bytes=resource_size(&distributor);
    platform->cpu_interface=cpu.start;platform->cpu_interface_bytes=resource_size(&cpu);n130_gic_probed=1;return 0;
}
int n130_gic_final(void)
{
    struct gic_chip_data *gic=&gic_data[0];
    void __iomem *distributor,*cpu;unsigned int i;u32 control;
    if(!READ_ONCE(n130_gic_probed) || num_online_cpus()!=1)return -ENODEV;
    distributor=gic_data_dist_base(gic);cpu=gic_data_cpu_base(gic);
    local_irq_disable();
    /* Active IRQs are not force-completed; a live owner is a refusal. Never read IAR. */
    for(i=0;i<gic->gic_irqs;i+=32)if(readl_relaxed(distributor+GIC_DIST_ACTIVE_SET+i/8))return -EBUSY;
    for(i=0;i<gic->gic_irqs;i+=32){
        writel_relaxed(~0U,distributor+GIC_DIST_ENABLE_CLEAR+i/8);
        writel_relaxed(~0U,distributor+GIC_DIST_PENDING_CLEAR+i/8);
    }
    /* The retained XNU source adopts nonsecure GICv2 with both EOImode bits clear. */
    control=readl_relaxed(cpu+GIC_CPU_CTRL);
    control=(control&GICC_DIS_BYPASS_MASK)|GICC_ENABLE;
    writel_relaxed(GICC_INT_PRI_THRESHOLD,cpu+GIC_CPU_PRIMASK);
    writel_relaxed(control,cpu+GIC_CPU_CTRL);
    writel_relaxed(GICD_ENABLE,distributor+GIC_DIST_CTRL);dsb(sy);
    if(!(readl_relaxed(distributor+GIC_DIST_CTRL)&GICD_ENABLE) ||
       !(readl_relaxed(cpu+GIC_CPU_CTRL)&GICC_ENABLE) ||
       (readl_relaxed(cpu+GIC_CPU_CTRL)&(BIT(9)|BIT(10))))return -EIO;
    /* Timer is still disabled; existing target IRQ bridge enables its verified PPI. */
    if(readl_relaxed(distributor+GIC_DIST_CONFIG+4)&BIT((30-16)*2+1))return -EINVAL;
    return 0;
}
