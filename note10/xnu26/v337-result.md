# v337 gives the network-policy key generation a diagnostic random source and stops before a dtrace pseudo-device assert: objective met

**Safety, return and objective PASS.** Source `8c5fefa` built successfully on the first attempt in CI run `45130188015` (one dispatch). The v337 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N337PS20`, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted checkpoint was reached.** Core 0 stopped at the `mlukt` checkpoint, in no interrupt identification slot.

In v336 core 0 stopped at the `necp_rng` checkpoint, just before network-policy initialisation called the corecrypto random-number generator through the crypto function table, whose random-number entry was left empty on purpose in v325. The user approved replacing only the two network-policy key generation calls with XNU's own software random-number function, which at this point in boot draws from the same early-boot generator XNU had already used many times. No corecrypto entry was filled or faked.

v337 bundles:

- **Network-policy keys from XNU's own software generator (user-approved).** The two key generation calls in network-policy initialisation now call XNU's own software random-number function with the same buffer and length. The result of the original call was never checked, so nothing else changes. The crypto function table is untouched and its random-number entry is still empty.
- **`necp_rng` checkpoint removed.** The v336 checkpoint is restored to ordinary code.
- **New checkpoint before the dtrace assert.** The emulation showed that the next stop is a release assertion in an early dtrace pseudo-device initialisation, which would trap because the device tree does not declare a property that one kernel-text check expects. v337 places a masked checkpoint, `mlukt`, at the start of that assertion path, so the assertion trap is never executed. The assertion itself and the normal path are unchanged.
- **Backstops.** The IOKit BSD init stop and the v334 root-device lookup stop both stay, so no IOKit BSD publish, root-device lookup or storage matching can run. Neither was expected to be reached.
- **Kept.** The v336 kernel translation fault filter and panic stops, the v335 diagnostic TCP Fast Open AES skip, the v334 diagnostic pthread function-table stub, the v333 IORTC wait skip, the v332 platform-start return, the v330 one-shot SPI disable, the v329 PMU quiesce, the v328 filter (interrupt 30 serviced by XNU, any other ID spins at its slot without acknowledge), the FIQ, SError and earlier markers, and the v333 return qualification from the reset timing all remain. No device-tree change and no new device write.
- **Caveats.**
  - The network-policy keys come from a diagnostic generator. Randomness is predictable, as already accepted in v324, the per-CPU random contexts are dummies, and no integrity cryptography, AES or corecrypto random-number entry is provided.
  - Only kernel translation faults are handled; user-space faults, other abort types and all other exception classes still stop.
  - Panics are stop markers; XNU's panic and debugger machinery has not run.
  - TCP Fast Open is disabled; this is not an AES implementation.
  - The pthread table is still a diagnostic fake kext interface, not a pthread implementation.
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - The platform is XNU's generic base class, not a driver for this board. No RTC driver exists, so the calendar starts from software time only.
  - The watchdog reset restores the GIC for the normal return.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v336.
- **Offline prediction (emulation only).** The emulator carried the v330 timer, PMU and interrupt 502 models and the v336 synchronous-exception model unchanged.
  - In that emulation the same single kernel translation fault as in v336 occurred and was resolved by XNU; no other fault occurred.
  - Both network-policy key calls went to XNU's software generator and filled their keys; the corecrypto random-number call was not entered.
  - XNU then completed network agent, memory-status, sysctl and keyboard-mapping initialisation, entered the pseudo-device init loop and stopped at the `mlukt` checkpoint, with no panic, refused access or further fault.
  - XNU mapped only the GIC distributor and CPU interface, the device accesses equalled the v336 set, no new system-register class was written, and no storage, root-device, IOKit BSD or process-creation path was entered.
  - No counter-run was made.

On the device, the stub ran every check, committed the `N337PS2T` record and branched to XNU. The record was bound to the current build, boot and cycle.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `mlukt` checkpoint, as predicted. The reset followed the last keepalive inside the bound, so the controller granted the return qualification. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness were set to 10 in the cycle and both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** On the device, with the two network-policy key calls served by XNU's own software generator, XNU got past network-policy initialisation, through network agent, memory-status, sysctl and keyboard-mapping initialisation, and stopped just before the dtrace pseudo-device assertion. None of the class, other-abort, kernel-fault-panic or panic stop markers was reached, and neither the IOKit BSD nor the root-device backstop was reached. The stop address comes from the boot loader's reset report.

**What this does not show.**

- That every step between network-policy init and the dtrace assert behaved as in the emulator. The device shows only the final stop.
- That randomness is of usable quality. The keys come from a predictable diagnostic generator, the corecrypto random-number entry is still empty and TCP Fast Open is disabled.
- That XNU can handle any other kind of fault or exception, or that its panic path works. Those still stop.
- That pthread support works. The table is a stand-in; no user thread or synchronisation path has run.
- That the calendar time is correct. There is no RTC driver.
- How many timer interrupts XNU serviced on the device. The filter leaves no trace for ID 30.
- That any device XNU later needs works. All SPIs still stay disabled until XNU itself enables them.

Next is the dtrace pseudo-device assertion. Going past this checkpoint needs a decision on how the kernel-text check is satisfied for diagnostic boots (for example a device-tree property or a diagnostic skip), or a stop here, which is a user decision. Further on, `bsd_init` reaches the IOKit BSD publish and root-device lookup, which need a no-storage policy decision before any block driver runs; the backstops stay until then. A board-specific platform expert, interrupt policy for devices XNU will use, a real pthread kext, real AES and randomness, trust-cache handling and independent native return remain unproven.
