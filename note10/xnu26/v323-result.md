# v323 XNU reaches a read_random call, the predicted stop after libkern and IOKit initialization

**Qualification PASS.** Source `974d66db679dd5d5391b99d50b42c942ae1829f8` built successfully on the first attempt in CI run `44980399726`. The v323 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N323PS20`, so the cycle ran a new reviewed build and no spent build was replayed.

In v322 core 0 stopped at the checkpoint after `OSlibkernInit`'s call to `OSRuntimeInitializeCPP`. That checkpoint replaced the call's success test. So the device showed that the call returned, not that it reported success.

v323 bundles:

- **Checkpoint removed.** The original success test after `OSRuntimeInitializeCPP` is restored. XNU can now finish `OSlibkernInit`, `InitIOKit` and `PE_init_iokit` and return into `kernel_bootstrap_thread`.
- **New checkpoint.** A private patch turns the entry of `read_random` into a self-spin. The offline analysis shows that this kernel has no registered kernel PRNG. `prng_funcs.generate` is still NULL, because this image has no prelinked kexts, and so no corecrypto kext calls `register_and_init_prng`. Without the checkpoint, the first `read_random` call would branch to address 0 and end at the shared synchronous-exception marker. The dedicated spin names the stop and halts before that branch.
- **Markers kept.** The v322 synchronous-exception and IRQ markers and the earlier markers remain.
- **Unchanged.** boot_args, the device tree, the seed, the handoff layout, the stub, the Linux code, the bootstrap map limit and the reservation are identical to v322.
- **Offline prediction.** Before use, the image was emulated with the v322 model. That model handles top-byte-tagged pointers, logs interrupt-mask changes and allows only the six v321 GIC accesses. In that emulation:
  - the success test passed and `PE_init_iokit` returned
  - `kernel_bootstrap_thread` moved to its next startup phase, where the startup entry `exe_boothash_salt_generate` (no boot-arg set) called `read_random` and stopped at the new checkpoint
  - interrupts stayed masked, and there was no device access beyond the v321 GIC accesses

  A counter-run without the checkpoint reproduced the fault on the NULL generator. The first prediction attempt refused because of a stop-address bug in the emulator and wrote nothing. The bug was fixed under independent review before the accepted run.

On the device, the stub ran every check, committed the `N323PS2T` record and branched to XNU. The record, bound to the current build, boot and cycle, matched the precomputed values exactly.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `read_random` entry checkpoint spin, as predicted. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

This qualifies the build as far as the checkpoint shows. The device shows only that core 0 was in the `read_random` entry spin at the reset, so some call to `read_random` was reached. Core 0 was not in the synchronous-exception or IRQ marker, any earlier marker, `_panic_spin_forever` or the debugger trap path. That is consistent with the offline prediction. Several points come from the offline emulation, not from the device:

- the caller was `exe_boothash_salt_generate`
- the success test after `OSRuntimeInitializeCPP` passed
- IOKit initialization completed
- interrupts stayed masked, with no further device access

Next is providing a kernel PRNG, which is the role the corecrypto kext would normally fill, so that `read_random` works. That starts with a read-only assessment of the `prng_funcs` interface. The first interrupt unmask is expected soon after and will need the reviewed interrupt-path analysis. Kernel PRNG operation, interrupt handling and independent native return remain unproven.
