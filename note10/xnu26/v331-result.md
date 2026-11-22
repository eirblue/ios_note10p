# v331 runs the generic platform expert past IOPanicPlatform::start: objective met

**Safety, return and objective PASS.** Source `6047b2c96122f1bfeafbeec29f9ee2c912803909` built successfully on the first attempt in CI run `45045664013`. The v331 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N331PS20`, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted platform-expert checkpoint was reached.** Core 0 stopped at the `pe_started` checkpoint, after the base `IOPlatformExpert::start` returned true, and in no interrupt identification slot.

In v330 core 0 stopped at the `IOPanicPlatform::start` checkpoint. IOKit matching picks `IOPanicPlatform` for the root platform device because nothing else matches. A read-only scan found no board-specific platform-expert subclass in the image, and `IOPanicPlatform` inherits the base class's power-domain and configure methods unchanged. That identification is offline analysis, not device evidence.

v331 bundles:

- **Generic platform start.** A private patch rewrites the start of `IOPanicPlatform::start`, inside that one function:
  - it calls the base `IOPlatformExpert::start` with the same object and provider, so XNU's own generic code sets the platform, instantiates the power-management root domain and runs configure
  - it then masks interrupts and stops at one of two checkpoints, `pe_started` if start returned true or `pe_start_false` if it returned false
  - the old panic call is left in place but is no longer reached

  No code cave, no new class, no device-tree change and no new device write. The earlier masked `IOPanicPlatform::start` checkpoint is removed.
- **Filter, SPI disable and markers kept.** The v330 one-shot SPI disable, the v329 PMU quiesce, the v328 filter (interrupt 30 serviced by XNU, any other ID spins at its slot without acknowledge), and the FIQ, SError, synchronous-exception and earlier markers all remain.
- **Caveats.**
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - Randomness is predictable, the per-CPU random contexts are dummies, and no integrity cryptography is provided.
  - The platform is XNU's generic base class, not a driver for this board. The device tree carries no platform UUID or serial, so none is published.
  - The watchdog reset restores the GIC for the normal return.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v330.
- **Offline prediction.** The emulator carried the v330 timer, PMU and interrupt 502 models unchanged.
  - In that emulation the base start ran to completion, returned true and XNU stopped at the `pe_started` checkpoint, with no panic, refused access or fault.
  - XNU mapped only the GIC distributor and CPU interface, the device accesses equalled the v330 set, and no new system-register class was written.
  - No counter-run was made; the v330 counter-run already covers the SPI disable.

On the device, the stub ran every check, committed the `N331PS2T` record and branched to XNU. The record, bound to the current build, boot and cycle, matched the precomputed values exactly.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `pe_started` checkpoint, as predicted. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** With the generic platform expert standing in for a board-specific one, `IOPlatformExpert::start` ran to completion on the device and returned true, so XNU now has a registered platform and a power-management root domain.

**What this does not show.**

- How many timer interrupts XNU serviced on the device. The filter leaves no trace for ID 30.
- That every step inside the base start behaved as in the emulator. The device shows only that it returned true.
- That other threads woken by the published platform made progress. Core 0 is the only core observed.
- That any device XNU later needs works. All SPIs still stay disabled until XNU itself enables them.

Next is to remove the checkpoint and let IOKit continue to the next blocking point. Root-device and storage paths need a no-storage policy decision before any block driver runs. Interrupt policy for devices XNU will use, a board-specific platform expert, trust-cache handling and independent native return remain unproven.
