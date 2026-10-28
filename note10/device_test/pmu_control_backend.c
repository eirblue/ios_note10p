/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in pinned ARMv8 perf_event.c after the original backend functions. */
#include <linux/note10_pmu_control_audit.h>
#include <linux/note10_pm_preconditions.h>
#include <asm/cputype.h>
int n10_ctl_backend(struct arm_pmu *p,struct n10_ctl_row *r,unsigned int generation)
{
    struct pmu_hw_events *hw;u64 el,midr,dfr,mmfr,pmcr,cnt,ints;unsigned int i;int num,ret=0;
    if (!p || !r || !n10_pre_context(generation,1,1) || in_interrupt()) return -EPERM;
    num=READ_ONCE(p->num_events);
    if (num<1 || num>32 || !READ_ONCE(p->hw_events) || !cpumask_test_cpu(0,&p->supported_cpus)) return -EINVAL;
    if (READ_ONCE(p->start)!=armv8pmu_start || READ_ONCE(p->stop)!=armv8pmu_stop ||
        READ_ONCE(p->reset)!=armv8pmu_reset || READ_ONCE(p->enable)!=armv8pmu_enable_event ||
        READ_ONCE(p->disable)!=armv8pmu_disable_event || READ_ONCE(p->read_counter)!=armv8pmu_read_counter ||
        READ_ONCE(p->write_counter)!=armv8pmu_write_counter) return -ENODEV;
    /* Inherited unchanged higher-EL/security regime: a synchronous MRS fault is not caught. */
    el=read_sysreg(CurrentEL);midr=read_sysreg(midr_el1);
    dfr=read_sysreg(id_aa64dfr0_el1);mmfr=read_sysreg(id_aa64mmfr0_el1);
    if (el!=4 || (midr & MIDR_CPU_MODEL_MASK)!=MIDR_CORTEX_A55 || MIDR_VARIANT(midr)!=1 || MIDR_REVISION(midr)!=0 ||
        ((dfr>>8)&15)!=4 || (mmfr>>24)!=0) return -ENODEV;
    hw=this_cpu_ptr(p->hw_events);
    if (!raw_spin_trylock(&hw->pmu_lock)) return -EBUSY;
    if (!n10_pre_context(generation,1,2) || in_interrupt()) { ret=-EPERM;goto unlock; }
    pmcr=read_sysreg(pmcr_el0);
    if ((pmcr>>32) || (((pmcr>>ARMV8_PMU_PMCR_N_SHIFT)&ARMV8_PMU_PMCR_N_MASK)+1)!=(unsigned int)num) { ret=-EIO;goto unlock; }
    cnt=read_sysreg(pmcntenset_el0);ints=read_sysreg(pmintenset_el1);
    if ((cnt>>32) || (ints>>32)) { ret=-EIO;goto unlock; }
    r->num=num;r->kind=5;r->current_el=1;r->model_match=1;r->variant=1;r->revision=0;r->pmuver=4;r->fgt=0;
    r->pmcr=(u32)pmcr;r->cntenset=(u32)cnt;r->intenset=(u32)ints;
    r->visible_phys=(1U<<31)|((1U<<(num-1))-1U);
    for (i=0;i<(unsigned int)num;i++) if (test_bit(i,hw->used_mask)) {
        r->used_sw|=1U<<i;r->used_phys|=1U<<ARMV8_IDX_TO_COUNTER(i);
    }
unlock:
    raw_spin_unlock(&hw->pmu_lock);
    if (!n10_pre_context(generation,1,1) || in_interrupt()) return -EPERM;
    return ret;
}
