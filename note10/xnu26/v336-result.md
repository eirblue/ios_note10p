# v336 lets XNU resolve the skywalk first-touch kernel page fault itself and stops before the first network random-number call: objective met

**Safety, return and objective PASS.** Source `b152eaf` built successfully on the first attempt in CI run `45120738755` (one dispatch). The v336 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N336PS20`, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted checkpoint was reached.** Core 0 stopped at the `necp_rng` checkpoint, in no interrupt identification slot.

In v335 core 0 stopped at the `skmem_sysctl` checkpoint, just before skywalk memory initialisation made its first store into a pageable kernel page that had no mapping yet. The user approved letting XNU's own synchronous exception handler and `vm_fault` run for diagnostic boots, but only for kernel translation faults. An offline emulation with synchronous exceptions modelled showed XNU resolving that fault itself and continuing; the next natural stop is not the IOKit BSD publish but `necp_init`, which calls the corecrypto random-number generator through the crypto function table, whose random-number entry was left empty on purpose in v325. That identification is offline analysis, not device evidence.

v336 bundles:

- **Kernel translation faults go to XNU (user-approved).** A short filter in front of XNU's synchronous exception handler passes an exception on to the stock handler only when it is a data abort taken in the kernel, on a kernel virtual address, with a translation fault status. Every other exception class and every other abort ends at its own masked stop marker. The handler, `vm_fault` and the page-table code are XNU's own, unmodified.
- **Panic paths stopped.** The kernel-state panic entry and the common panic funnel are replaced by masked stop markers, so an unresolvable fault or any panic stops before XNU's debugger, panic log or platform hooks run.
- **Skywalk checkpoint removed.** The v335 `skmem_sysctl` checkpoint is restored to the stock call, so the first touch happens and is handled by XNU.
- **New checkpoint before the random-number call.** In `necp_init`, the call into the random-number generator is replaced by a masked checkpoint, `necp_rng`, so the empty crypto entry is never called. No random-number entry is provided or faked.
- **Backstops.** A new masked stop on the IOKit BSD init call in `bsd_init` and the v334 root-device lookup stop both stay, so no IOKit BSD publish, root-device lookup or storage matching can run. Neither was expected to be reached.
- **Kept.** The v335 diagnostic TCP Fast Open AES skip, the v334 diagnostic pthread function-table stub, the v333 IORTC wait skip, the v332 platform-start return, the v330 one-shot SPI disable, the v329 PMU quiesce, the v328 filter (interrupt 30 serviced by XNU, any other ID spins at its slot without acknowledge), the FIQ, SError and earlier markers, and the v333 return qualification from the reset timing all remain. No device-tree change and no new device write.
- **Caveats.**
  - Only kernel translation faults are handled; user-space faults, other abort types and all other exception classes still stop.
  - Panics are stop markers; XNU's panic and debugger machinery has not run.
  - TCP Fast Open is disabled; this is not an AES implementation, and the random-number entry is still empty.
  - The pthread table is still a diagnostic fake kext interface, not a pthread implementation.
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - Randomness is predictable, the per-CPU random contexts are dummies, and no integrity cryptography, AES or random-number entry is provided.
  - The platform is XNU's generic base class, not a driver for this board. No RTC driver exists, so the calendar starts from software time only.
  - The watchdog reset restores the GIC for the normal return.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v335.
- **Offline prediction.** The emulator carried the v330 timer, PMU and interrupt 502 models unchanged and added a faithful synchronous-exception model in which XNU's own vector, handler, `vm_fault` and page-table code run on the modelled memory.
  - In that emulation exactly one synchronous exception occurred: the skywalk first store faulted, the filter passed it, XNU's handler called `vm_fault`, which took one page from XNU's free-page cache, zeroed it and entered one kernel page-table entry, and the exception return resumed the same store, which then completed. No page-table page was added, no TLB maintenance was needed and no interrupt or GIC access occurred inside the handler.
  - XNU then finished skywalk initialisation, started one more kernel thread for the nexus domains, entered `necp_init`, completed the NECP client initialisation and stopped at the `necp_rng` checkpoint, with no panic, refused access or further fault.
  - Without that checkpoint the emulation took a second exception, an instruction fetch at address zero from the empty random-number entry, which the filter routed to the class stop marker.
  - XNU mapped only the GIC distributor and CPU interface, the device accesses equalled the v335 set, no new system-register class was written, and no storage, root-device, IOKit BSD or process-creation path was entered.
  - No counter-run was made.

On the device, the stub ran every check, committed the `N336PS2T` record and branched to XNU. The record was bound to the current build, boot and cycle.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `necp_rng` checkpoint, as predicted. The reset followed the last keepalive inside the bound, so the controller granted the return qualification. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness were set to 10 in the cycle and both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** On the device, with only kernel translation faults routed to XNU's own handler, XNU got past the skywalk first-touch point, finished network control initialisation up to NECP and stopped just before its first random-number call. None of the class, other-abort, kernel-fault-panic or panic stop markers was reached, and neither the IOKit BSD nor the root-device backstop was reached. The stop address comes from the boot loader's reset report. Reaching a stop beyond the skywalk first touch is consistent with XNU having resolved that fault itself.

**What this does not show.**

- That every step between skywalk memory init and NECP behaved as in the emulator, or that exactly one fault was taken. The device shows only the final stop.
- That XNU can handle any other kind of fault or exception, or that its panic path works. Those still stop.
- That randomness, TCP Fast Open or any AES-based network path works. The random-number entry is empty and TCP Fast Open is disabled.
- That pthread support works. The table is a stand-in; no user thread or synchronisation path has run.
- That the calendar time is correct. There is no RTC driver.
- How many timer interrupts XNU serviced on the device. The filter leaves no trace for ID 30.
- That any device XNU later needs works. All SPIs still stay disabled until XNU itself enables them.

Next is the first random-number call in `necp_init`. Going past this checkpoint needs either a diagnostic random-number source for that call, a diagnostic skip of it, or a stop here, which is a user decision. The emulator look-ahead past that call, with both NECP random-number calls skipped in emulation only, next stops in the dtrace pseudo-device init on a kernel assertion trap, still before the IOKit BSD publish. Further on, `bsd_init` reaches the IOKit BSD publish and root-device lookup, which need a no-storage policy decision before any block driver runs; the backstops stay until then. A board-specific platform expert, interrupt policy for devices XNU will use, a real pthread kext, real AES and randomness, trust-cache handling and independent native return remain unproven.
