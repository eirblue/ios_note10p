// SPDX-License-Identifier: GPL-2.0-only
/* Built-in diagnostic for a future manually booted temporary Linux kernel.
 * No MMIO, CPU hotplug, MMU changes, partition access or XNU invocation.
 * Linux on_each_cpu supplies a preemption/IRQ-safe per-CPU callback context.
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/smp.h>
#include <asm/barrier.h>
#include <asm/sysreg.h>

#define N10_REG(name) ((unsigned long)read_sysreg(name))

static void n10_capture_cpu(void *unused)
{
    unsigned int cpu = smp_processor_id(), level, type;
    unsigned long saved = read_sysreg(csselr_el1);
    unsigned long clidr = read_sysreg(clidr_el1);
    unsigned long selector, value;

    (void)unused;
    pr_info("N10CAP1 CPU cpu=%u el=%lx mpidr=%lx mmfr0=%lx mmfr1=%lx isar1=%lx clidr=%lx ctr=%lx cntfrq=%lx\n",
            cpu, N10_REG(CurrentEL), N10_REG(mpidr_el1),
            N10_REG(id_aa64mmfr0_el1), N10_REG(id_aa64mmfr1_el1),
            N10_REG(id_aa64isar1_el1), clidr, N10_REG(ctr_el0),
            N10_REG(cntfrq_el0));
    for (level = 0; level < 7; ++level) {
        type = (clidr >> (level * 3)) & 7;
        if (type == 2 || type == 3 || type == 4) {
            selector = level << 1;
            write_sysreg(selector, csselr_el1);
            isb();
            value = read_sysreg(ccsidr_el1);
            pr_info("N10CAP1 CACHE cpu=%u selector=%lu value=%lx\n", cpu, selector, value);
        }
        if (type == 1 || type == 3) {
            selector = (level << 1) | 1;
            write_sysreg(selector, csselr_el1);
            isb();
            value = read_sysreg(ccsidr_el1);
            pr_info("N10CAP1 CACHE cpu=%u selector=%lu value=%lx\n", cpu, selector, value);
        }
    }
    write_sysreg(saved, csselr_el1);
    isb();
    pr_info("N10CAP1 RESTORE cpu=%u before=%lx after=%lx\n", cpu, saved,
            N10_REG(csselr_el1));
}

static int __init n10_capture_init(void)
{
    pr_info("N10CAP1 BEGIN online=%u\n", num_online_cpus());
    on_each_cpu(n10_capture_cpu, NULL, 1);
    pr_info("N10CAP1 END online=%u\n", num_online_cpus());
    return 0;
}
late_initcall(n10_capture_init);
