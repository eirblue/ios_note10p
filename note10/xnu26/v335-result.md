# v335 skips only the TCP Fast Open AES key setup and stops in skywalk memory init before the first pageable page touch: objective met

**Safety, return and objective PASS.** Source `3d13576` built successfully on the first attempt in CI run `45102737327` (one dispatch). The v335 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N335PS20`, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted checkpoint was reached.** Core 0 stopped at the `skmem_sysctl` checkpoint, in no interrupt identification slot.

In v334 core 0 stopped at the `tcp_aes` checkpoint, where `tcp_init` sets up the TCP Fast Open key with AES through the crypto function table, whose AES entry was left empty on purpose in v325. The user chose a diagnostic skip of only that key-setup call, with TCP Fast Open disabled. An offline emulation then showed that the next natural stop is not crypto: inside `bsd_init`, skywalk memory initialisation allocates a pageable kernel region and its sysctl setup makes the first store into it. That page has no mapping yet; XNU would fill it on first touch through its synchronous exception handler, which is still a stop marker in these builds. That identification is offline analysis, not device evidence.

v335 bundles:

- **Diagnostic TCP Fast Open AES skip (user-approved).** A private image patch removes only the call into the AES key setup in `tcp_init` and sets TCP Fast Open to disabled for client and server, so the unset key can never reach the empty AES entry later. No AES is provided or faked, and the crypto table is unchanged from v325. The v334 `tcp_aes` checkpoint is removed.
- **New checkpoint before the first pageable touch.** In skywalk memory initialisation, the call into the sysctl setup is replaced by a masked checkpoint, `skmem_sysctl`, directly after the region is allocated and before its first page is touched.
- **Root-device backstop.** The v334 masked checkpoint on the root-device lookup call in `bsd_init` stays, so no root-device or storage matching can run even if the device path differs from the emulation. It was not expected to be reached.
- **Kept.** The v334 diagnostic pthread function-table stub, the v333 IORTC wait skip, the v332 platform-start return, the v330 one-shot SPI disable, the v329 PMU quiesce, the v328 filter (interrupt 30 serviced by XNU, any other ID spins at its slot without acknowledge), the FIQ, SError, synchronous-exception and earlier markers, and the v333 return qualification from the reset timing all remain. No device-tree change and no new device write.
- **Caveats.**
  - TCP Fast Open is disabled; this is not an AES implementation.
  - The pthread table is still a diagnostic fake kext interface, not a pthread implementation.
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - Randomness is predictable, the per-CPU random contexts are dummies, and no integrity cryptography or AES is provided.
  - The platform is XNU's generic base class, not a driver for this board. No RTC driver exists, so the calendar starts from software time only.
  - The watchdog reset restores the GIC for the normal return.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v334.
- **Offline prediction.** The emulator carried the v330 timer, PMU and interrupt 502 models unchanged.
  - In that emulation `tcp_init` ran for the IPv4 and IPv6 protocol tables without entering any AES function, the SYN-cookie setup used only the random source, and the IPsec, flow-divert and tap initialisation ran on software tables. `bsd_init` then entered skywalk initialisation and its memory init, and XNU stopped at the `skmem_sysctl` checkpoint, with no panic, trap entry, refused access or fault.
  - Without that checkpoint the emulation faulted on the first store into the unmapped pageable page, which on the device would end at the anonymous synchronous-exception marker.
  - XNU mapped only the GIC distributor and CPU interface, the device accesses equalled the v334 set, no new system-register class was written, no new kernel thread was started, the crypto table was read only at the two entries already used since v325, and no storage, root-device or process-creation path was entered.
  - No counter-run was made.

On the device, the stub ran every check, committed the `N335PS2T` record and branched to XNU. The record was bound to the current build, boot and cycle.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `skmem_sysctl` checkpoint, as predicted. The reset followed the last keepalive inside the bound, so the controller granted the return qualification. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness were set to 10 in the cycle and both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** On the device, XNU completed `tcp_init` with only the TCP Fast Open key setup skipped, finished the remaining protocol initialisation, entered skywalk memory initialisation and stopped before the first touch of a pageable kernel page. No AES path, no pthread trap checkpoint and no root-device backstop was reached. The stop address comes from the boot loader's reset report.

**What this does not show.**

- That every step between `tcp_init` and skywalk memory init behaved as in the emulator. The device shows only the final stop.
- That XNU can fill a pageable kernel page on first touch. Its synchronous exception handler has not run on the device.
- That TCP Fast Open or any AES-based network path works. It is disabled.
- That pthread support works. The table is a stand-in; no user thread or synchronisation path has run.
- That the calendar time is correct. There is no RTC driver.
- How many timer interrupts XNU serviced on the device. The filter leaves no trace for ID 30.
- That any device XNU later needs works. All SPIs still stay disabled until XNU itself enables them.

Next is the first pageable page touch in skywalk memory init. Going past this checkpoint needs either letting XNU's synchronous exception handler resolve kernel page faults for diagnostic boots, a diagnostic skip of that skywalk first touch, or a stop here, which is a user decision. Further on, `bsd_init` reaches the IOBSD publish and root-device lookup, which need a no-storage policy decision before any block driver runs; the backstop stays until then. A board-specific platform expert, interrupt policy for devices XNU will use, a real pthread kext, real AES, trust-cache handling and independent native return remain unproven.
