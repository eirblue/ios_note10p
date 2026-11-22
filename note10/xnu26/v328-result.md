# v328 stops on a pending shared interrupt, ID 173: objective not met

**Safety and return PASS; objective NOT met.** Source `6233eed71d1654c9b4795478da68ea631bf81d45` built successfully on the first attempt in CI run `45014200660`. The v328 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N328PS20`, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted `IOPanicPlatform::start` checkpoint was not reached.** Core 0 stopped in the identification slot for interrupt ID 173, which the design treated as a distinct, non-objective outcome.

In v327 the highest-priority pending interrupt at XNU's IRQ entry was ID 30, the EL1 physical timer interrupt that XNU arms itself.

v328 bundles:

- **Timer-only interrupt filter.** A private patch turns the v327 dispatcher into a filter. It still reads `GICC_HPPIR` without acknowledging anything.
  - If the highest-priority pending ID is 30, the filter runs the instruction it displaced and continues into XNU's real `sleh_irq`. XNU's own interrupt handler then acknowledges the timer at the GIC, re-arms it through `rtclock_intr` and signals end of interrupt.
  - Any other ID still branches to its self-spin slot with no acknowledge, as in v327.
- **Markers kept.** The FIQ, SError, synchronous-exception and earlier markers remain, as does the `IOPanicPlatform::start` checkpoint.
- **Caveats.**
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - Randomness is predictable, the per-CPU random contexts are dummies, and no integrity cryptography is provided.
  - XNU now writes the GIC CPU interface's acknowledge and end-of-interrupt registers for interrupt 30, under the reviewed per-device analysis.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v327.
- **Offline prediction.** The emulator gained timer interrupt injection: modeled timer expiry, exception entry, XNU's handler and return. In that emulation one timer interrupt was injected, and XNU serviced it through acknowledge and end-of-interrupt, continued IOKit matching and stopped at the `IOPanicPlatform::start` checkpoint. Counter-runs without injection, and with the pending ID forced to 27, ended at the checkpoint and at slot 27 respectively. The emulator models only the timer interrupt. No other interrupt source is modeled.

On the device, the stub ran every check, committed the `N328PS2T` record and branched to XNU. The record, bound to the current build, boot and cycle, matched the precomputed values exactly.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped in the slot for interrupt ID 173, not at the predicted checkpoint. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** At some IRQ entry on core 0, the highest-priority pending interrupt visible at the GIC CPU interface was ID 173. That ID comes from the slot core 0 stopped in. By the GIC architecture, IDs 32 and above are shared peripheral interrupts (SPIs), so 173 is an SPI, number 141 in device-tree numbering. It was not acknowledged. Most likely it is a device interrupt that Linux left enabled and routed to CPU 0, but that is inference, not device evidence.

**What this does not show.**

- Whether any earlier timer interrupts were taken and serviced by XNU's handler. The filter leaves no trace for ID 30, so the device result neither confirms nor rules out timer servicing.
- Which device owns interrupt 173. That is still to be identified.
- That 173 was the only interrupt pending, or that it raised this particular exception. The register reports only the highest-priority interrupt at the moment of the read.
- Where XNU was when the interrupt arrived.

Next is identifying the source of interrupt 173 and deciding a policy for interrupts Linux leaves enabled. One option is for XNU to disable that interrupt, which needs its own analysis and owner decision. Timer servicing on the device, interrupt policy, IOKit platform matching, trust-cache handling and independent native return remain unproven.
