# v329 stops on a different pending shared interrupt, ID 502: objective not met

**Safety and return PASS; objective NOT met.** Source `0cb4dd0b9d49ebeffc533a118d5a93de3c1a3320` built successfully on the first attempt in CI run `45023302870`. The v329 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N329PS20`, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted `IOPanicPlatform::start` checkpoint was not reached.** Core 0 stopped in the identification slot for interrupt ID 502, which the design treated as a distinct, non-objective outcome.

In v328 core 0 stopped in the slot for ID 173, a shared peripheral interrupt (SPI). A read-only analysis afterwards identified ID 173 as CPU 0's ARMv8 PMU overflow interrupt. The likely mechanism is a performance counter still programmed by Linux on CPU 0 that overflows while XNU runs, raising a level-triggered interrupt. That identification is offline analysis, not device evidence.

v329 bundles:

- **PMU quiesce at the source.** A private patch redirects XNU's first interrupt-unmask call through a short stub that runs on CPU 0 just before the unmask. The stub uses only CPU 0's own PMU system registers (`PMINTENCLR_EL1`, `PMCNTENCLR_EL0`, `PMOVSCLR_EL0`):
  - disable every overflow interrupt
  - stop all counters
  - clear all overflow flags, so the level drops

  It then continues into `ml_set_interrupts_enabled`. It makes no GIC or other device write.
- **Filter and markers kept.** The v328 filter (interrupt 30 serviced by XNU, any other ID spins at its slot without acknowledge), the FIQ, SError, synchronous-exception and earlier markers, and the `IOPanicPlatform::start` checkpoint all remain.
- **Caveats.**
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - Randomness is predictable, the per-CPU random contexts are dummies, and no integrity cryptography is provided.
  - XNU acknowledges and ends interrupt 30 at the GIC CPU interface. CPU 0's PMU state, as left by Linux, is discarded.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v328.
- **Offline prediction.** The emulator added a CPU 0 PMU model with interrupt 173 pending from the start, as the worst case.
  - In that emulation the stub cleared it before the unmask. XNU serviced its timer interrupt and stopped at the `IOPanicPlatform::start` checkpoint.
  - A counter-run with the stub unreachable reproduced the v328 stop in slot 173.
  - The emulator models only the timer and this PMU interrupt. No other interrupt source is modeled.

On the device, the stub ran every check, committed the `N329PS2T` record and branched to XNU. The record, bound to the current build, boot and cycle, matched the precomputed values exactly.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped in the slot for interrupt ID 502, not at the predicted checkpoint. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** At some IRQ entry on core 0, the highest-priority pending interrupt visible at the GIC CPU interface was ID 502. That ID comes from the slot core 0 stopped in. ID 502 is an SPI, number 470 in device-tree numbering. It was not acknowledged. Interrupt 173 was not the highest-pending interrupt at that entry. That is consistent with the PMU quiesce having worked.

**What this does not show.**

- That the PMU quiesce worked. The device leaves no direct trace of the stub, and interrupt 173 might simply not have been pending at that moment, or might have been pending at a lower priority than 502.
- Which device owns interrupt 502. That is still to be identified.
- Whether any timer interrupts were serviced by XNU's handler before this point.
- That 502 was the only interrupt pending, or that it raised this particular exception.
- Where XNU was when the interrupt arrived.

Next is identifying the source of interrupt 502 and applying the same source-first policy where possible. Each further Linux-left interrupt needs its own analysis, and a broader policy may need an owner decision. Timer servicing on the device, interrupt policy, IOKit platform matching, trust-cache handling and independent native return remain unproven.
