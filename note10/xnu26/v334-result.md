# v334 passes pthread initialisation with a diagnostic stub and stops in tcp_init before AES key setup: objective met

**Safety, return and objective PASS.** Source `cc0f49c` built successfully on the first attempt in CI run `45088076758` (one dispatch). The v334 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N334PS20`, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted checkpoint was reached.** Core 0 stopped at the `tcp_aes` checkpoint, in no interrupt identification slot.

In v333 core 0 stopped at the `pthread_null` checkpoint, where `bsd_init` initialises pthread support and finds no pthread kernel extension registered. Stock XNU panics there. The user chose to go past this point with a diagnostic pthread function-table stand-in. An offline emulation then showed the next natural stop inside `tcp_init`: it sets up the TCP Fast Open key with AES through the crypto function table, and the AES entry there was left empty on purpose in v325. That identification is offline analysis, not device evidence.

v334 bundles:

- **Diagnostic pthread function-table stub (user-approved).** A private image patch restores the stock pthread initialisation and gives the kernel a static, read-only function table in place of the missing pthread kext. Its initialisation entry returns immediately; every other entry leads to a distinct trap checkpoint, so an unexpected call would be identified, not run. This is a fake kext interface for diagnostic boots only: no user thread, synchronisation or work-queue service behind it works. The v333 `pthread_null` checkpoint is removed.
- **New checkpoint before the empty AES entry.** In `tcp_init`, the call into the AES key setup is replaced by a masked checkpoint, `tcp_aes`. No AES is provided or faked, and the crypto table is unchanged from v325.
- **Root-device backstop.** The root-device lookup call in `bsd_init` is replaced by a masked checkpoint, so no root-device or storage matching can run even if the device path differs from the emulation. It was not expected to be reached.
- **Kept.** The v333 IORTC wait skip, the v332 platform-start return, the v330 one-shot SPI disable, the v329 PMU quiesce, the v328 filter (interrupt 30 serviced by XNU, any other ID spins at its slot without acknowledge), the FIQ, SError, synchronous-exception and earlier markers, and the v333 return qualification from the reset timing all remain. No device-tree change and no new device write.
- **Caveats.**
  - The pthread table is a diagnostic fake kext interface, not a pthread implementation.
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - Randomness is predictable, the per-CPU random contexts are dummies, and no integrity cryptography or AES is provided.
  - The platform is XNU's generic base class, not a driver for this board. No RTC driver exists, so the calendar starts from software time only.
  - The watchdog reset restores the GIC for the normal return.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v333.
- **Offline prediction.** The emulator carried the v330 timer, PMU and interrupt 502 models unchanged.
  - In that emulation the pthread initialisation called only the stub's initialisation entry, once. `bsd_init` then ran the shared-memory and semaphore caches, the network work queue, the interface layer (its new kernel threads were each scheduled by ordinary scheduling), socket and protocol-domain initialisation, IP and `tcp_init`, and XNU stopped at the `tcp_aes` checkpoint, with no panic, trap entry, refused access or fault.
  - XNU mapped only the GIC distributor and CPU interface, the device accesses equalled the v333 set, no new system-register class was written, and no storage, root-device or process-creation path was entered.
  - No counter-run was made.

On the device, the stub ran every check, committed the `N334PS2T` record and branched to XNU. The record was bound to the current build, boot and cycle.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `tcp_aes` checkpoint, as predicted. The reset followed the last keepalive inside the bound, so the controller granted the return qualification. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness were set to 10 in the cycle and both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** On the device, XNU ran `bsd_init` past the pthread initialisation with the stub table, through the network and protocol-domain initialisation, into `tcp_init`, and stopped before the AES key setup whose crypto entry is intentionally absent. No pthread trap checkpoint and no root-device backstop was reached. The stop address comes from the boot loader's reset report.

**What this does not show.**

- That every step between the pthread initialisation and `tcp_init` behaved as in the emulator. The device shows only the final stop.
- That pthread support works. The table is a stand-in; no user thread or synchronisation path has run.
- That the calendar time is correct. There is no RTC driver.
- How many timer interrupts XNU serviced on the device. The filter leaves no trace for ID 30.
- That any device XNU later needs works. All SPIs still stay disabled until XNU itself enables them.

Next is the AES gap in `tcp_init`. Going past this checkpoint needs either skipping the TCP Fast Open key setup for diagnostic boots or a stop here, which is a user decision. Further on, `bsd_init` reaches root-device lookup, which needs a no-storage policy decision before any block driver runs; the backstop stays until then. A board-specific platform expert, interrupt policy for devices XNU will use, a real pthread kext, trust-cache handling and independent native return remain unproven.
