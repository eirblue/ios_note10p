# v338 answers the kernel-text-patch safety query as 'restricted' and stops before IOKit BSD init: objective met

**Safety, return and objective PASS.** Source `9bfb3d9` built successfully on the first attempt in CI run `45136003761` (one dispatch). The v338 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N338PS20`, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted checkpoint was reached.** Core 0 stopped at the `iokitbsd` checkpoint, in no interrupt identification slot.

In v337 core 0 stopped at the `mlukt` checkpoint, at the start of a release assertion in an early dtrace pseudo-device initialisation. The assertion fires when the kernel asks whether its text may be patched at run time and the device tree does not declare the property that answers it. The user approved changing only that assertion path so the query answers 'restricted', the same answer the kernel gives when kernel text protection is enabled. The query's normal path, its initialisation and its flags are unchanged, and no device-tree property was added.

v338 bundles:

- **Kernel-text-patch query answers 'restricted' (user-approved).** The assertion path of the query now returns 'not unsafe' to the original caller instead of trapping. Every consumer then takes its stock 'restricted' branch: the dtrace kernel-text patching probes are refused, and kernel text is never patched at run time. dtrace initialisation is not skipped; each dtrace pseudo-device init runs its own code.
- **`mlukt` checkpoint removed.** The v337 checkpoint is now ordinary code.
- **Bundle end at IOKit BSD init.** The emulation found no further software-only blocker before IOKit BSD init. That step is the storage and root-device boundary, which needs a separate user decision, so the existing IOKit BSD init stop is now the predicted stop. The v334 root-device lookup stop stays as a backstop.
- **Kept.** The v337 network-policy key source, the v336 kernel translation fault filter and panic stops, the v335 diagnostic TCP Fast Open AES skip, the v334 diagnostic pthread function-table stub, the v333 IORTC wait skip, the v332 platform-start return, the v330 one-shot SPI disable, the v329 PMU quiesce, the v328 filter (interrupt 30 serviced by XNU, any other ID spins at its slot without acknowledge), the FIQ, SError and earlier markers, and the v333 return qualification from the reset timing all remain. No device-tree change and no new device write.
- **Caveats.**
  - The 'restricted' answer is a diagnostic stand-in. The device tree still does not declare kernel text protection, and no hardware text protection was configured or shown.
  - dtrace kernel-text probes are refused for this boot; no dtrace probe was exercised.
  - The network-policy keys come from a diagnostic generator. Randomness is predictable, the per-CPU random contexts are dummies, and no integrity cryptography, AES or corecrypto random-number entry is provided.
  - Only kernel translation faults are handled; user-space faults, other abort types and all other exception classes still stop.
  - Panics are stop markers; XNU's panic and debugger machinery has not run.
  - TCP Fast Open is disabled; this is not an AES implementation.
  - The pthread table is still a diagnostic fake kext interface, not a pthread implementation.
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - The platform is XNU's generic base class, not a driver for this board. No RTC driver exists, so the calendar starts from software time only.
  - The watchdog reset restores the GIC for the normal return.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v337.
- **Offline prediction (emulation only).** The emulator carried the v330 timer, PMU and interrupt 502 models and the v336 synchronous-exception model unchanged.
  - In that emulation the same single kernel translation fault as in v336 and v337 occurred and was resolved by XNU; no other fault occurred.
  - The kernel-text query answered 'restricted'; the two dtrace pseudo-devices that patch kernel text refused their probes, and the other dtrace pseudo-devices registered with their stock code.
  - XNU then finished the BSD pseudo-device init loop and stopped at the `iokitbsd` checkpoint, immediately before IOKit BSD init, with no panic, refused access or further fault.
  - XNU mapped only the GIC distributor and CPU interface, the device accesses equalled the v337 set, no new system-register class was written, and no storage, root-device, IOKit BSD or process-creation path was entered.
  - No counter-run was made.

On the device, the stub ran every check, committed the `N338PS2T` record and branched to XNU. The record was bound to the current build, boot and cycle.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `iokitbsd` checkpoint, as predicted. The reset followed the last keepalive inside the bound, so the controller granted the return qualification. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness were set to 10 in the cycle and both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** On the device, with the kernel-text-patch query answering 'restricted', XNU got past the dtrace pseudo-device assertion, finished BSD pseudo-device initialisation and stopped immediately before IOKit BSD init. None of the class, other-abort, kernel-fault-panic or panic stop markers was reached, the old `mlukt` stop did not appear, and the root-device backstop was not reached. No storage or root-device access took place. The stop address comes from the boot loader's reset report.

**What this does not show.**

- That every step between the dtrace assertion and IOKit BSD init behaved as in the emulator. The device shows only the final stop.
- That kernel text is protected. The 'restricted' answer is a diagnostic stand-in; no hardware text protection is configured.
- That dtrace works. Its kernel-text probes are refused and no probe has run.
- That randomness is of usable quality. The keys come from a predictable diagnostic generator, the corecrypto random-number entry is still empty and TCP Fast Open is disabled.
- That XNU can handle any other kind of fault or exception, or that its panic path works. Those still stop.
- That pthread support works. The table is a stand-in; no user thread or synchronisation path has run.
- That the calendar time is correct. There is no RTC driver.
- How many timer interrupts XNU serviced on the device. The filter leaves no trace for ID 30.
- That any device XNU later needs works. All SPIs still stay disabled until XNU itself enables them.

Next is IOKit BSD init, the storage and root-device boundary. Going past this checkpoint needs a user decision on a no-storage policy before any block driver or root-device lookup can run, or a stop here; the backstops stay until then. A board-specific platform expert, interrupt policy for devices XNU will use, real kernel text protection, a real pthread kext, real AES and randomness, trust-cache handling and independent native return remain unproven.
