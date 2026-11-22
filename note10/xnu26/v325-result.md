# v325 XNU reaches the predicted checkpoint before its first interrupt unmask

**Qualification PASS.** Source `1d6507bac0d6153065468fd0af9f74266c3ec53a` built successfully on the first attempt in CI run `44990475155`. The v325 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N325PS20`, so the cycle ran a new reviewed build and no spent build was replayed.

In v324 core 0 stopped at the checkpoint on the entry of `crypto_random_kmem_ctx_size`. The offline analysis had shown that XNU's corecrypto function table `g_crypto_funcs` is NULL. Only the corecrypto kext registers it, and this image has none.

v325 bundles:

- **Minimal corecrypto function table.** A private patch supplies a static `crypto_functions` table and points `g_crypto_funcs` at it. Only the four random-number entries are filled: generate, uniform, kmem context size and kmem init. Short stubs back them with XNU's own early-random DRBG. Every digest, HMAC, cipher and RSA entry stays NULL. The v324 checkpoint is removed.
- **Caveats.** This table is for diagnostic boots only:
  - All randomness is predictable, because the device-tree seed is a fixed public pattern.
  - The per-CPU random contexts are dummies.
  - No integrity cryptography is provided. Any later caller of a digest, HMAC, cipher or RSA entry would reach a NULL entry.
- **New checkpoint.** A self-spin on `kernel_bootstrap_thread`'s call to `ml_set_interrupts_enabled(TRUE)`, its first interrupt unmask. The checkpoint sits on the call, so XNU stops before unmasking. Interrupt safety at the unmask cannot yet be shown, because the set of interrupts Linux leaves routed to CPU 0 is unknown.
- **Markers kept.** The synchronous-exception, IRQ and earlier markers remain.
- **Unchanged.** boot_args, the device tree, the seed, the handoff layout, the stub, the Linux code, the bootstrap map limit and the reservation are identical to v324.
- **Offline prediction.** Before use, the image was emulated with the v324 model. In that emulation:
  - the random entries served `vm_map_store_crypto_init`, and that startup phase completed
  - `kernel_bootstrap_thread` reached the unmask call and stopped at the new checkpoint
  - interrupts stayed masked, and there was no device access beyond the v321 GIC accesses

  Two counter-runs confirmed the setup:
  - With the checkpoint removed, the run unmasked interrupts at that call and later reached XNU's trust-cache panic, `image4 interface not available`. That panic follows from the absent AppleImage4 kext.
  - Without the table, the run faulted on the NULL function table, as in v324.

On the device, the stub ran every check, committed the `N325PS2T` record and branched to XNU. The record, bound to the current build, boot and cycle, matched the precomputed values exactly.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the pre-unmask checkpoint spin, as predicted. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

This qualifies the build as far as the checkpoint shows. The device shows only that core 0 was in the spin at the unmask call site at the reset. Core 0 was not in the synchronous-exception or IRQ marker, any earlier marker, `_panic_spin_forever` or the debugger trap path. That is consistent with the offline prediction. Several points come from the offline emulation, not from the device:

- the random entries served `vm_map_store_crypto_init`
- the startup phase completed
- interrupts stayed masked, with no further device access

Two decisions are needed before going further:

- **Interrupt policy at the first unmask.** One option is for XNU to disable the interrupts Linux left enabled, which needs its own per-device analysis. The other is to accept the race, bounded by the IRQ marker.
- **The trust-cache / image4 stop.** Bypassing it would disable code-signing trust policy, so it is an integrity decision for the user and reviewer.

Interrupt handling, trust-cache handling, integrity cryptography and independent native return remain unproven.
