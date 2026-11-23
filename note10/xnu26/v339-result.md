# v339 runs XNU's storage and root bring-up with a RAM-only memory ramdisk and stops at the root-mount attempt: objective met

**Safety, return and objective PASS.** Source `b9aa41a` built successfully on the first attempt in CI run `45159581507` (one dispatch). The v339 fixture (3 groups, 6 variants, 6 assertions) passed; earlier checks were not replayed. The v321 validator, the v316 stub and the v316 Linux sources were reused unchanged. The public changes are the record tag `N339PS20`, a root-device boot argument on the kernel command line and one diagnostic memory device property in the device tree's memory map, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted checkpoint was reached.** Core 0 stopped at the `noroot` checkpoint, in no interrupt identification slot.

In v338 core 0 stopped at the `iokitbsd` checkpoint, immediately before IOKit BSD init, the storage and root-device boundary. The user approved going past it with a RAM-only memory ramdisk registered as the boot root candidate. The ramdisk is a small zero-filled region inside the existing handoff page, below the kernel's data end. No new RAM range, no storage driver and no real partition is involved.

v339 bundles:

- **RAM-only memory ramdisk as the root candidate (user-approved).** The command line names the memory device as the root, and the device tree's memory map declares the ramdisk region. XNU's stock root lookup registers the memory device from that property and selects it as the root device.
- **IOKit BSD init and root lookup restored.** The v338 `iokitbsd` stop and the v334 root-device lookup backstop are stock code again.
- **Two absent-storage-class assertions.** This bare kernel has no storage family classes. Two release assertions that fire only because those classes are absent now take the stock path for an empty root medium, which is what a kernel with the storage family present does for a memory root.
- **Bundle end at the root-mount attempt.** XNU attempts to mount the root and stops at the new `noroot` checkpoint, before the 'cannot mount root' message and its retry loop. A success backstop after the mount stays in place but is unreachable in this image.
- **Kept.** The v338 kernel-text-patch 'restricted' answer, the v337 network-policy key source, the v336 kernel translation fault filter and panic stops, the v335 diagnostic TCP Fast Open AES skip, the v334 diagnostic pthread function-table stub, the v333 IORTC wait skip, the v332 platform-start return, the v330 one-shot SPI disable, the v329 PMU quiesce, the v328 filter (interrupt 30 serviced by XNU, any other ID spins at its slot without acknowledge), the FIQ, SError and earlier markers, and the v333 return qualification from the reset timing all remain. No new device write.
- **Caveats.**
  - The ramdisk is a diagnostic stand-in. It holds no filesystem, and its bytes are never read or written.
  - This diagnostic kernel build has no mountable filesystem compiled in, so the root mount cannot succeed whatever the ramdisk holds; the attempt ends without a mounted root.
  - The two assertion changes cover only the absent storage classes; no storage driver exists or was started.
  - The 'restricted' kernel-text answer is a diagnostic stand-in; no hardware text protection was configured or shown.
  - The network-policy keys come from a diagnostic generator. Randomness is predictable and no integrity cryptography, AES or corecrypto random-number entry is provided.
  - Only kernel translation faults are handled; user-space faults, other abort types and all other exception classes still stop.
  - Panics are stop markers; XNU's panic and debugger machinery has not run.
  - TCP Fast Open is disabled; this is not an AES implementation.
  - The pthread table is still a diagnostic fake kext interface, not a pthread implementation.
  - Code-signing trust is not enforced, because trust caches are not loaded. No user-space code ran.
  - The platform is XNU's generic base class, not a driver for this board. No RTC driver exists, so the calendar starts from software time only.
  - The watchdog reset restores the GIC for the normal return.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v338.
- **Offline prediction (emulation only).** The emulator carried the v330 timer, PMU and interrupt 502 models and the v336 synchronous-exception model unchanged.
  - In that emulation the same single kernel translation fault as in v336 to v338 occurred and was resolved by XNU; no other fault occurred.
  - IOKit BSD init ran and published the BSD resource; IOKit matching started no driver.
  - The root lookup registered the memory device from the ramdisk property and selected it as the root.
  - The mount attempt opened the root device without any data I/O, found no root-capable filesystem and did not mount it. XNU then stopped at the `noroot` checkpoint, with no panic, refused access or further fault.
  - XNU mapped only the GIC distributor and CPU interface. The extra device accesses compared with v338 all fell inside one extra timer interrupt delivery, no new system-register class was written, and no storage driver, block I/O, user-space or process-creation path was entered.
  - No counter-run was made.

On the device, the stub ran every check, committed the `N339PS2T` record and branched to XNU. The record was bound to the current build, boot and cycle.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `noroot` checkpoint, as predicted. The reset followed the last keepalive inside the bound, so the controller granted the return qualification. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness were set to 10 in the cycle and both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** On the device, with a RAM-only memory ramdisk registered as the boot root candidate, XNU ran IOKit BSD init and its storage and root bring-up path, attempted a root mount and stopped at the `noroot` checkpoint. None of the class, other-abort, kernel-fault-panic or panic stop markers was reached, the old `iokitbsd` stop and the root-device lookup backstop did not appear, and the mount success backstop was not reached. No ramdisk I/O was performed, no real storage or partition was touched and no new MMIO was mapped. The stop address comes from the boot loader's reset report.

**What this does not show.**

- That every step between IOKit BSD init and the mount attempt behaved as in the emulator. The device shows only the final stop.
- That XNU can mount a root filesystem. This build has no mountable filesystem, and the ramdisk holds no filesystem.
- That any storage driver or real block device works. None exists in this image and none was used.
- That user space can start. No launchd or other user-space code exists or ran.
- That kernel text is protected. The 'restricted' answer is a diagnostic stand-in.
- That randomness is of usable quality. The keys come from a predictable diagnostic generator, the corecrypto random-number entry is still empty and TCP Fast Open is disabled.
- That XNU can handle any other kind of fault or exception, or that its panic path works. Those still stop.
- That pthread support works. The table is a stand-in; no user thread or synchronisation path has run.
- That the calendar time is correct. There is no RTC driver.
- How many timer interrupts XNU serviced on the device. The filter leaves no trace for ID 30.
- That any device XNU later needs works. All SPIs still stay disabled until XNU itself enables them.

Next is the root mount itself. Going past this checkpoint needs a kernel build with a root-capable filesystem and a root image with user-space code, which is outside the current approval and image; the backstops stay until then. A board-specific platform expert, storage drivers, interrupt policy for devices XNU will use, real kernel text protection, a real pthread kext, real AES and randomness, trust-cache handling and independent native return remain unproven.
