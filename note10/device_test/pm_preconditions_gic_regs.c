/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in the pinned GIC TU. Exactly 12 benign banked reads; no writes. */
#include <linux/note10_pm_preconditions.h>
int n10_pre_gic_regs(unsigned int phase, struct n10_precond_gic_row *r, u32 ctlr, u32 pmr)
{
    void __iomem *dist; u32 expected,mode;unsigned int i;
    if (!r || phase>2 || r->seen++ || raw_smp_processor_id()!=0 ||
        num_online_cpus()!=1 || cpumask_bits(cpu_online_mask)[0]!=1 ||
        preempt_count()!=1 || !!irqs_disabled()!=(phase==1) || !gic_data[0].domain) return -EIO;
    dist=gic_data_dist_base(&gic_data[0]);if (!dist)return -ENODEV;
    r->enable=readl_relaxed(dist+GIC_DIST_ENABLE_SET);
    r->active=readl_relaxed(dist+GIC_DIST_ACTIVE_SET);
    for (i=0;i<2;i++) r->config[i]=readl_relaxed(dist+GIC_DIST_CONFIG+i*4);
    for (i=0;i<8;i++) r->priority[i]=readl_relaxed(dist+GIC_DIST_PRI+i*4);
    mode=static_key_true(&supports_deactivate) ? GIC_CPU_CTRL_EOImodeNS : 0;
    expected=(ctlr&GICC_DIS_BYPASS_MASK)|mode|GICC_ENABLE;
    r->restore_matches=(ctlr==expected && pmr==GICC_INT_PRI_THRESHOLD);
    for (i=0;i<8;i++) if (r->priority[i]!=GICD_INT_DEF_PRI_X4)r->restore_matches=0;
    return 0;
}
