# v333 skips the IORTC wait and stops where bsd_init initialises pthread: objective met

**Safety, return and objective PASS.** Source `4d07a54` built successfully on the first attempt in CI run `45068283340` (one dispatch). The v333 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N333PS20`, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted checkpoint was reached.** Core 0 stopped at the `pthread_null` checkpoint, in no interrupt identification slot.

In v332 core 0 stopped at the `rtc_wait` checkpoint inside `IOKitInitializeTime`, called from `bsd_init`. The stock code there waits up to 30 seconds for an `IORTC` service. The image has no kernel extensions, so no RTC driver can ever register and that wait always ends by timeout. An offline emulation then showed `bsd_init` panicking a little later, because the pthread kernel extension never registered its function table. That identification is offline analysis, not device evidence.

v333 bundles:

- **IORTC wait skipped.** A private patch removes the `IORTC` matching and the 30-second wait in `IOKitInitializeTime`, so it goes straight to the calendar clock initialisation. This is the path the stock code reaches after its timeout, without the 30 seconds. The `rtc_wait` checkpoint is removed.
- **New checkpoint before the pthread panic.** In the pthread initialisation called from `bsd_init`, the panic call taken when no pthread kext is registered is replaced by a masked checkpoint, `pthread_null`. The panic text and its function stay in the image but are no longer reached. No code cave, no new class, no device-tree change and no new device write.
- **Platform start, filter, SPI disable and markers kept.** The v332 platform-start return, the v330 one-shot SPI disable, the v329 PMU quiesce, the v328 filter (interrupt 30 serviced by XNU, any other ID spins at its slot without acknowledge), and the FIQ, SError, synchronous-exception and earlier markers all remain.
- **Return qualification from the reset timing.** In v332 the controller judged the watchdog return by how long the host took to see normal TWRP again, and that host-side latency failed the cycle although the device had returned safely. The v333 controller instead reads, from the boot log bound to this build, boot and cycle, the time of the actor's last watchdog keepalive and the time the boot loader logged the following reset, and requires the reset to follow within a bound set by the watchdog timeout. Missing, duplicated or out-of-order lines fail closed. The host return latency is still recorded, as an observation only. The 240-second return limit, the armed watchdog and the five-partition check are unchanged, and the new term controls no write, reboot or retry. The brightness readback timeout was also raised, with a single attempt.
- **Caveats.**
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - Randomness is predictable, the per-CPU random contexts are dummies, and no integrity cryptography is provided.
  - The platform is XNU's generic base class, not a driver for this board. No RTC driver exists, so the calendar starts from software time only.
  - The watchdog reset restores the GIC for the normal return.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v332.
- **Offline prediction.** The emulator carried the v330 timer, PMU and interrupt 502 models unchanged.
  - In that emulation `IOKitInitializeTime` ran without entering the `IORTC` matching or wait, the calendar clock initialised, `bsd_init` ran its following initialisers and XNU stopped at the `pthread_null` checkpoint, with no panic, refused access or fault.
  - XNU mapped only the GIC distributor and CPU interface, the device accesses equalled the v332 set, no new system-register class was written, and no storage or root-device path was entered.
  - No counter-run was made; the v330 counter-run already covers the SPI disable.

On the device, the stub ran every check, committed the `N333PS2T` record and branched to XNU. The record was bound to the current build, boot and cycle.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `pthread_null` checkpoint, as predicted. The reset followed the last keepalive inside the bound, so the controller granted the return qualification. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness were set to 10 in the cycle and both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** On the device, XNU ran `bsd_init` past the RTC setup and its following initialisers to the pthread initialisation, and found no pthread kext registered. That is the point where stock XNU would panic. The stop address comes from the boot loader's reset report.

**What this does not show.**

- That every step between the RTC setup and the pthread initialisation behaved as in the emulator. The device shows only the final stop.
- That the calendar time is correct. There is no RTC driver.
- How many timer interrupts XNU serviced on the device. The filter leaves no trace for ID 30.
- That any device XNU later needs works. All SPIs still stay disabled until XNU itself enables them.

Next is the pthread kext gap. Going past this checkpoint needs either a diagnostic pthread function-table stand-in or a stop here, which is a user decision. Further on, `bsd_init` reaches root-device lookup, which needs a no-storage policy decision before any block driver runs. A board-specific platform expert, interrupt policy for devices XNU will use, trust-cache handling and independent native return remain unproven.
