/* Single-CPU XNU IRQ bridge. GIC initialization/mapping is a caller prerequisite. */
#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)
#include <mach/vm_types.h>
#include <machine/machine_routines.h>
#include <arm/rtclock.h>
#include <kern/debug.h>
#include <pexpert/arm/protos.h>
#include "note10/gicv2_mmio.h"

static struct n10_gic_mmio_view note10_view;
static struct n10_gic_io note10_io;
static uint32_t note10_irq_count, note10_timer_intid;
static int note10_irq_ready;

static void
note10_require_cpu_context(void)
{
    const ml_topology_info_t *topology=ml_get_topology_info();
    if (!topology || topology->num_cpus!=1 || ml_get_interrupts_enabled())
        panic("Note10 IRQ: single CPU and masked interrupts required");
}

void
pe_note10_bind_irq(vm_offset_t distributor, vm_size_t distributor_size,
    vm_offset_t cpu_interface, vm_size_t cpu_size, uint32_t timer_intid)
{
    note10_require_cpu_context();
    if (note10_irq_ready || timer_intid<16 || timer_intid>=32)
        panic("Note10 IRQ: invalid or repeated binding");
    note10_view=(struct n10_gic_mmio_view){distributor,cpu_interface,distributor_size,cpu_size};
    if (!n10_gic_mmio_bind(&note10_view,&note10_io))
        panic("Note10 IRQ: invalid mapped windows");
    struct n10_gic_info info;
    uint32_t distributor_ctl, cpu_ctl;
    if (n10_gic_probe(&note10_io,&info)!=N10_GIC_OK ||
        !note10_io.read(note10_io.context,N10_GIC_DISTRIBUTOR,0,&distributor_ctl) ||
        !note10_io.read(note10_io.context,N10_GIC_CPU,0,&cpu_ctl) ||
        !(distributor_ctl&1) || !(cpu_ctl&1) || (cpu_ctl&((1U<<9)|(1U<<10))))
        panic("Note10 IRQ: initialized nonsecure EOImode0 GIC required");
    /* Group/security ownership, priority and trigger setup are caller-owned. */
    if (n10_gic_set_enabled(&note10_io,info.irq_count,timer_intid,1)!=N10_GIC_OK)
        panic("Note10 IRQ: cannot enable timer PPI");
    note10_irq_count=info.irq_count;
    note10_timer_intid=timer_intid;
    note10_irq_ready=1;
}

void
pe_note10_handle_irq(void)
{
    note10_require_cpu_context();
    if (!note10_irq_ready) panic("Note10 IRQ: platform binding missing");
    struct n10_gic_irq irq;
    enum n10_gic_result status=n10_gic_take(&note10_io,note10_irq_count,&irq);
    if (status==N10_GIC_SPECIAL) return;
    if (status!=N10_GIC_OK) panic("Note10 IRQ: acknowledge failed");
    if (irq.intid!=note10_timer_intid) panic("Note10 IRQ: unimplemented interrupt source");

    /* Mask the level source across the callback/EOI. rtclock_intr must rearm
     * through the physical decrementer selected by patch 0002.
     */
    __builtin_arm_wsr64("CNTP_CTL_EL0",3);
    __builtin_arm_isb(15);
    note10_rtclock_intr(1);
    if (n10_gic_complete(&note10_io,note10_irq_count,&irq)!=N10_GIC_OK)
        panic("Note10 IRQ: completion failed");
    __builtin_arm_wsr64("CNTP_CTL_EL0",1);
    __builtin_arm_isb(15);
}
#endif
