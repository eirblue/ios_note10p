# v332 returns from the platform expert and reaches the IORTC wait in bsd_init: cycle FAILED on return timing

**Objective met; safety held; cycle NOT passed.** Source `45944b0` built successfully on the first attempt in CI run `45059979649` (one dispatch). The v332 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N332PS20`, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted checkpoint was reached.** Core 0 stopped at the `rtc_wait` checkpoint, in no interrupt identification slot. **The cycle is still recorded as failed (`passed=false`)**, because normal TWRP returned later than the controller's conservative fallback deadline, so the record-binding and return qualification were not granted. It is not counted as a PASS.

In v331 core 0 stopped at the `pe_started` checkpoint, after the base `IOPlatformExpert::start` returned true. An offline emulation then showed that only returning from start is not enough. The kernel bootstrap thread waits in `ml_wait_max_cpus` for a signal that only a CPU interrupt-controller driver sends, and the image has no such driver. Every thread then blocks and the CPU idles at no fixed address. That identification is offline analysis, not device evidence.

v332 bundles:

- **Platform start returns.** A private patch rewrites the start of `IOPanicPlatform::start`, inside that one function:
  - it calls the base `IOPlatformExpert::start` as before and keeps its result
  - it then calls XNU's own `ml_set_max_cpus`, the call the missing interrupt-controller driver would make, so the bootstrap thread is released
  - it returns the start result to IOKit's `startCandidate`

  The `pe_started` and `pe_start_false` checkpoints are removed.
- **New checkpoint before the RTC wait.** In `IOKitInitializeTime`, called from `bsd_init`, the 30-second wait for an `IORTC` service is replaced by a masked checkpoint, `rtc_wait`. No code cave, no new class, no device-tree change and no new device write.
- **Filter, SPI disable and markers kept.** The v330 one-shot SPI disable, the v329 PMU quiesce, the v328 filter (interrupt 30 serviced by XNU, any other ID spins at its slot without acknowledge), and the FIQ, SError, synchronous-exception and earlier markers all remain.
- **Caveats.**
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - Randomness is predictable, the per-CPU random contexts are dummies, and no integrity cryptography is provided.
  - The platform is XNU's generic base class, not a driver for this board. Calling `ml_set_max_cpus` from the platform start stands in for a driver that does not exist.
  - The watchdog reset restores the GIC for the normal return.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v331.
- **Offline prediction.** The emulator carried the v330 timer, PMU and interrupt 502 models unchanged.
  - In that emulation start returned true, the bootstrap thread resumed, `bsd_init` ran to `IOKitInitializeTime`, and XNU stopped at the `rtc_wait` checkpoint, with no panic, refused access or fault.
  - XNU mapped only the GIC distributor and CPU interface, every interrupt delivered was ID 30, and no new system-register class was written.
  - No counter-run was made; the v330 counter-run already covers the SPI disable.

On the device, the stub ran every check, committed the `N332PS2T` record and branched to XNU.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `rtc_wait` checkpoint, as predicted. Normal TWRP returned in a distinct boot epoch about 72 seconds after the actor started. That is within the 240-second bound but about 9 seconds past the controller's conservative fallback deadline of about 63 seconds (the watchdog's remaining time of about 68 seconds at the actor's acknowledgement, less a 5-second margin). Because of that, the controller did not grant the record-binding and return qualification, and it recorded the cycle as `failed-no-retry`. All five partition integrity checks passed. The controller's brightness readback timed out after the recovery set returned. In the same recovery boot, with no BOOT write and no reboot, the recovery setting and panel brightness were then set to 10 by hand and both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero. It was not retried.

**What this shows.** On the device, `IOPlatformExpert::start` returned to IOKit, the bootstrap thread got past `ml_wait_max_cpus`, and XNU ran `bsd_init` as far as the `IORTC` wait. That is the first stop inside BSD initialisation. The stop address comes from the boot loader's reset report.

**What this does not show.**

- A passing cycle. The return was late, so the controller's return qualification and record binding were not granted. The objective evidence comes from the breadcrumbs and the reset report, not from a passed cycle.
- Why the return took longer than in v329 and v331 (about 57 seconds each). The cause has not been identified.
- That every step between the platform start and `bsd_init` behaved as in the emulator. The device shows only the final stop.
- How many timer interrupts XNU serviced on the device. The filter leaves no trace for ID 30.
- That any device XNU later needs works. All SPIs still stay disabled until XNU itself enables them.

Next is the return timing: a passing cycle needs the normal return inside the controller's fallback deadline, or a reviewed change to that deadline. After the `IORTC` wait, the emulator shows `bsd_init` panicking because the pthread kernel extension is not loaded, and the image has no kexts. Getting past that likely needs a user decision. A board-specific platform expert, interrupt policy for devices XNU will use, trust-cache handling and independent native return remain unproven.
