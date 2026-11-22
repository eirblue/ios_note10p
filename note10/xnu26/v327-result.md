# v327 identifies the pending interrupt at XNU's IRQ entry as ID 30

**Qualification PASS.** Source `c6ae10e4328cd92847a2f559a9263b7ccbda2750` built successfully on the first attempt in CI run `45006641972`. The v327 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N327PS20`, so the cycle ran a new reviewed build and no spent build was replayed.

In v326 core 0 took an interrupt after XNU's own first unmask and stopped at the `sleh_irq` entry marker. The marker stopped before the interrupt was acknowledged, so the interrupt ID was unknown. It could have been the CPU 0 physical timer interrupt XNU had armed, or an interrupt Linux left enabled and routed to CPU 0.

v327 bundles:

- **Interrupt identification.** A private patch replaces the `sleh_irq` entry marker with a branch to a small dispatcher. The dispatcher reads the GIC-400 CPU interface's Highest Priority Pending Interrupt Register (`GICC_HPPIR`) through XNU's own GIC CPU-interface mapping. By the GIC architecture this read is side-effect-free: it does not acknowledge the interrupt or change its state. The dispatcher then jumps to one of 1024 self-spin slots indexed by the ID it read, so the core 0 program counter reported by the boot loader encodes the interrupt ID.
- **No memory breadcrumb.** After XNU's translation-table switch the boot log is not reachable, so the boot loader's PC report is the only channel.
- **Placement.** The dispatcher and slots occupy the body of an unused kernel self-test routine (`copyio_test`), which offline analysis confirms is never executed on this path.
- **Device access.** The new code makes one register read and no device writes.
- **Markers kept.** The FIQ, SError, synchronous-exception and earlier markers remain. The predicted `IOPanicPlatform::start` checkpoint from v326 remains as the no-interrupt outcome.
- **Caveats.**
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - Randomness is predictable, the per-CPU random contexts are dummies, and no integrity cryptography is provided.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v326.
- **Offline prediction.** The host model's timer log indicated that the interrupt was almost certainly XNU's own physical timer, interrupt 30. Unit runs of the dispatcher with IDs 30, 27, 32, 200 and 1023 each reached the matching slot.

On the device, the stub ran every check, committed the `N327PS2T` record and branched to XNU. The record, bound to the current build, boot and cycle, matched the precomputed values exactly.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped in the slot for interrupt ID 30, as predicted. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** When core 0 entered XNU's IRQ path, the highest-priority pending interrupt visible at the GIC CPU interface was ID 30. That ID comes from the slot core 0 stopped in. By the ARM generic-timer and GIC conventions, ID 30 is the private peripheral interrupt of the EL1 non-secure physical timer (CNTP). The offline analysis shows XNU arming that timer for its own deadline, so the interrupt is most likely XNU's own timer. The source attribution comes from public architecture facts plus offline analysis, not from the device.

**What this does not show.**

- That ID 30 was the only interrupt pending. The register reports only the highest-priority one at the moment of the read.
- That ID 30 is what raised this exception. A different interrupt could in principle have triggered the exception and then dropped before the read.
- Where XNU was when the interrupt arrived.
- Anything about XNU's interrupt handling, which has still not run.

Next is a reviewed path that lets XNU service interrupt 30 itself. Any other ID will keep spinning at its slot. That needs a per-device analysis of interrupt acknowledge and end-of-interrupt, and interrupt injection in the emulator to predict the timer servicing. Interrupt handling, IOKit platform matching, trust-cache handling and independent native return remain unproven.
