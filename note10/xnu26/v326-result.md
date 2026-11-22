# v326 XNU takes an interrupt after unmasking: the accepted alternative, not the predicted stop

**Qualification PASS (accepted alternative).** Source `94205d7bebac959ed590dafda8b4519e9ebe768f` built successfully on the first attempt in CI run `45001172051`. The v326 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N326PS20`, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted checkpoint was not reached.** The cycle ended at the interrupt marker, an outcome the design accepted in advance as meeting the objective.

In v325 core 0 stopped at the checkpoint on `kernel_bootstrap_thread`'s first call to `ml_set_interrupts_enabled(TRUE)`. Offline, the run past that point unmasked interrupts and later reached XNU's trust-cache panic, `image4 interface not available`. Two decisions were open: the interrupt policy at the first unmask, and the trust-cache stop. The project owner decided both for v326, choosing the most natural course on the user's instruction.

v326 bundles:

- **Trust-cache loading skipped.** A private patch turns `kernel_bootstrap_thread`'s calls to `trust_cache_runtime_init` and `load_static_trust_cache` into no-ops. No AppleImage4 interface is faked.
- **First interrupt unmask allowed.** The v325 checkpoint is removed, so XNU performs its own first unmask. That unmask also enables FIQ and SError delivery. So, in addition to the existing `sleh_irq` entry marker, new self-spins bound the entries of `sleh_fiq` and `sleh_serror`. Any interrupt or asynchronous error therefore stops at a distinct spin before XNU's handler runs. For an interrupt, that means before it is acknowledged at the GIC.
- **Predicted checkpoint.** A self-spin at the entry of `IOPanicPlatform::start`. Offline, after the unmask, XNU starts IOKit matching on its configuration thread. No platform driver matches the root compatible, so XNU falls back to `IOPanicPlatform`, which would panic with `Unable to find driver for this platform`.
- **Accepted alternative.** The design accepted both the checkpoint and the `sleh_irq` marker as meeting the objective. The emulator models no interrupt delivery, so it cannot predict whether a real interrupt arrives first.
- **Caveats.**
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - The v324 and v325 caveats still apply: randomness is predictable, the per-CPU random contexts are dummies, and no integrity cryptography is provided.
  - This build is for diagnostic boots only.
- **Unchanged.** boot_args, the device tree, the seed, the handoff layout, the stub, the Linux code, the bootstrap map limit and the reservation are identical to v325.
- **Offline prediction.** Before use, the image was emulated with the v325 model. In that emulation XNU unmasked interrupts, skipped the trust caches, began IOKit matching and stopped at the `IOPanicPlatform::start` checkpoint. Two counter-runs confirmed the setup:
  - Without the no-ops, the run reached the trust-cache panic.
  - With the v325 checkpoint left in place, the run stopped there as in v325.

On the device, the stub ran every check, committed the `N326PS2T` record and branched to XNU. The record, bound to the current build, boot and cycle, matched the precomputed values exactly.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `sleh_irq` entry marker spin, not at the predicted `IOPanicPlatform::start` checkpoint. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** Core 0 took an IRQ exception into XNU's vector and stopped at the `sleh_irq` entry before XNU's handler ran. This is the first interrupt taken by XNU on the device. Interrupts were masked through every earlier stage. The offline analysis places the only unmask on this path at XNU's own first unmask in `kernel_bootstrap_thread`. So the interrupt arrived after that unmask and before XNU reached the predicted checkpoint. Core 0 was not in the FIQ, SError or synchronous-exception markers, the predicted checkpoint, any earlier marker, `_panic_spin_forever` or the debugger trap path.

**What this does not show.**

- Which interrupt was taken. The marker stops before the interrupt is acknowledged, so no interrupt ID was read. It could be the CPU 0 physical timer interrupt XNU had armed, or an interrupt Linux left enabled and routed to CPU 0. Nothing here distinguishes the two.
- Where XNU was when the interrupt arrived.
- Whether the trust-cache no-ops or IOKit matching were reached on the device.
- Anything about XNU's interrupt handling.

The skip of trust-cache loading and the IOKit fallback path remain offline results.

Next is identifying the pending interrupt and deciding how XNU should service it. That needs a reviewed per-device analysis of interrupt acknowledge and end-of-interrupt, and an owner decision on interrupts Linux left enabled. Interrupt handling, IOKit platform matching, trust-cache handling and independent native return remain unproven.
