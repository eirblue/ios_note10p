# Paired CPU hotplug at the guarded noirq stop

v30 passed all 19 physical evaluations. Its 16 domain masks were zero at noirq,
all ones immediately after resume, then 0x4088 at 1.024, 5.120 and 15.104 seconds.
The next integrated test keeps those evaluations and adds three required items:
pm_cpus_noirq, cpu_stop_pmu_domains and pm_cpus_timers, for 22 total.

Default-off CONFIG_NOTE10_PM_CPUS_TEST adds a paired original hotplug call
inside the owned TEST_PLATFORM stop after successful late/noirq callbacks.
The suspend.c recipe and its fall-through guards stay unchanged. The observer
requires the same owned transaction, MEM state, local IRQs on, all eight CPUs
online and a successful preceding noirq PMU sample. It calls the pinned
disable_nonboot_cpus()/freeze_secondary_cpus(0), requires mask 0x01 and CPU0,
then always calls the original enable_nonboot_cpus(), including partial freeze
failures. Restored mask 0xff is mandatory. A restoration failure becomes EIO.
There is no new arch IRQ disable, syscore, sleep, MMU/cache or XNU entry path.
The enabled PM test runs on a dedicated unbound, non-freezable workqueue so its
caller is independent of a particular CPU's worker pool. The disabled profile
keeps the original scheduling behavior.

Original CPU code increments its hotplug-disable counter even on freeze
failure; enable is mandatory to balance it. Enable returns void and can leave
a CPU offline after an individual cpu_up error. Explicit online-mask checks
therefore decide acceptance rather than the return of enable.

A separate N10NPD1 bank reads the same 16 PMU_ALIVE tuples while the non-boot
CPUs are offline. It requires the successful noirq sample from the same
generation and performs 48 existing configuration/status/configuration reads.
It has no device locks, peripheral reads or added power requests. N10NPC1
records paired calls, masks, owner phase, CPU and original/final error.

After PM returns, N10NCT1 checks CNTKCTL_EL1 and CNTFRQ_EL0 on all eight CPUs
under the normal CPU read lock. It performs no register writes. Each restored
control value must match its pre-PM timer sample and frequency must be 26 MHz.
Each new lane requires consistent checksummed duplicate records from the same
transaction. Failed CPU attempts are reported; pre-device retries that never
ran hotplug emit no stale CPU sample.

PC validation passed 272 regressions, 90 actual suspend/noirq/hotplug integration
scenarios, 63 actual CPU-stop PMU scenarios, 28 pinned original hotplug scenarios
and 18 actual post-restore timer producer scenarios. Six scheduling adapter
scenarios cover queue allocation/retry failures and the
unchanged disabled path. The existing noirq, PMU,
FSYS and timed PMU models are also retained. CI and one fresh physical test
are pending. Screen logging stays off, and no raw device evidence is public.

These checks establish only their individually reported software and bounded
register observations. They do not establish complete global DMA shutdown,
secure-world quiescence, hardware GIC/MMU/cache handoff, XNU execution or iOS boot.
