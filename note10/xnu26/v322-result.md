# v322 XNU runs its C++ static constructors in corrected order and returns from the libkern C++ runtime setup

**Qualification PASS.** Source `dd07b67ec71f364604c7f5c997c8d46eb634881e` built successfully on the first attempt in CI run `44973667742`. The new v322 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N322PS20`, so the cycle ran a new reviewed build and no spent build was replayed.

In v321 core 0 stopped at the checkpoint placed directly after XNU's successful GIC bind. Offline, a lookahead past that point had stopped on a malformed pointer in the libkern symbol pool. v321 left that open as a possible emulator artifact.

The offline investigation for v322 traced the stop to a static-constructor order bug in this image, not to the emulator. In the image's constructor table (`__mod_init_func`), IOKit's `IONVRAM.cpp` initializer runs before libkern's `OSSymbol.cpp` initializer, and the libkern initializer is the one that sets up the `OSSymbol` pool. So the IONVRAM initializer calls `OSSymbol::withCString` on a pool that does not exist yet and follows an invalid pointer. The analysis concludes this would fault on hardware too.

v322 bundles:

- **Constructor-order fix.** A private data patch reorders the constructor table so all libkern constructors run before the IOKit ones. Relative order inside each group is kept, and the last kernel constructor stays last. This matches upstream link order (libkern before IOKit) and changes no code.
- **Checkpoint.** The v321 post-bind checkpoint is removed. A new checkpoint self-spin replaces the instruction after `OSlibkernInit`'s call to `OSRuntimeInitializeCPP`, which is where the call's result would normally be tested.
- **Safety markers.** New self-spins at the entries of XNU's synchronous-exception and IRQ handlers (`sleh_synchronous`, `sleh_irq`). Any unexpected exception or interrupt stops at a distinct spin before XNU's handlers run, so no interrupt acknowledge, end-of-interrupt or panic machinery is reached.
- **Unchanged.** boot_args, the device tree, the seed, the handoff layout, the stub, the Linux code, the bootstrap map limit and the reservation are identical to v321.
- **Offline prediction.** Before use, the emulator was improved to handle top-byte-tagged pointers and log interrupt-mask changes, and was limited to the six v321 GIC accesses. In that emulation XNU went through the following steps:
  - set up its timebase, programmed its timer registers with interrupts still masked, and made no device access beyond the v321 GIC accesses
  - finished early VM and zone bootstrap and started the kernel bootstrap thread
  - entered `PE_init_iokit` and `OSlibkernInit`
  - ran all static constructors in the corrected order and reached the new checkpoint

  A counter-run without the reorder reproduced the fault on the uninitialized symbol pool. On hardware that fault would end at the synchronous-exception marker. The first prediction attempt refused on an overly strict check and wrote nothing. The check was corrected under independent review before the accepted run.

On the device, the stub ran every check, committed the `N322PS2T` record and branched to XNU. The record, bound to the current build, boot and cycle, matched the precomputed values exactly.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the new checkpoint spin, as predicted. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

This qualifies the fix as far as the checkpoint shows. The device shows only that core 0 was in the checkpoint spin at the reset. It was not in the synchronous-exception or IRQ marker, any GIC or earlier marker, `_panic_spin_forever` or the debugger trap path. Because the checkpoint replaces the success test, it shows that the call to `OSRuntimeInitializeCPP` returned without a trapped exception. It does not show that the call reported success. That is consistent with the offline prediction. The corrected constructor order, the timer programming with interrupts masked and the absence of further device access all come from the offline emulation, not from the device.

Next is continuing into IOKit initialization and platform matching. The first point where XNU unmasks interrupts will need an interrupt-path safety analysis, checked against the approvals before design. IOKit bring-up, interrupt handling and independent native return remain unproven.
