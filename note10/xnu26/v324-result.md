# v324 XNU reaches the predicted corecrypto-function checkpoint after an in-kernel read_random backend

**Qualification PASS.** Source `fa5e3c888760fece517217bc93cb5e751c8cbf1d` built successfully on the first attempt in CI run `44985090505`. The v324 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N324PS20`, so the cycle ran a new reviewed build and no spent build was replayed.

In v323 core 0 stopped at the checkpoint on the entry of `read_random`. The offline analysis had shown that `prng_funcs.generate` is NULL. In this image no corecrypto kext runs `register_and_init_prng`, so the first `read_random` call would branch to address 0.

v324 bundles:

- **In-kernel read_random backend.** A private patch fills the two `prng_funcs` slots that `read_random` uses:
  - `refresh` points to a stub that simply returns.
  - `generate` points to a short stub that forwards to XNU's own `read_erandom_generate`. That is the early-random DRBG XNU already seeds from the `/chosen` `random-seed` property and the timebase.

  The `read_random` checkpoint is removed, and no other code changes.
- **Security caveat.** The device-tree seed is a fixed public pattern, so all randomness produced this way is predictable. This backend is for diagnostic boots only. It is not a kernel PRNG fit for any security use.
- **New checkpoint.** A self-spin at the entry of `crypto_random_kmem_ctx_size`. The offline analysis shows that this function reads XNU's corecrypto function table, `g_crypto_funcs`, which is also NULL because only the corecrypto kext registers it.
- **Markers kept.** The synchronous-exception, IRQ and earlier markers remain.
- **Unchanged.** boot_args, the device tree, the seed, the handoff layout, the stub, the Linux code, the bootstrap map limit and the reservation are identical to v323.
- **Offline prediction.** Before use, the image was emulated with the v323 model. In that emulation:
  - `read_random` returned data through the forwarding stub, and the startup entry that called it completed
  - `kernel_bootstrap_thread` went on to the startup entry `vm_map_store_crypto_init`, which calls `crypto_random_kmem_ctx_size` and stopped at the new checkpoint
  - interrupts stayed masked, and there was no device access beyond the v321 GIC accesses

  Two counter-runs confirmed the setup. Without the checkpoint, the run faulted on the NULL function table. Without the `prng_funcs` entries, it faulted on the branch to address 0, as in v323.

On the device, the stub ran every check, committed the `N324PS2T` record and branched to XNU. The record, bound to the current build, boot and cycle, matched the precomputed values exactly.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `crypto_random_kmem_ctx_size` entry checkpoint spin, as predicted. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

This qualifies the build as far as the checkpoint shows. The device shows only that core 0 was in the `crypto_random_kmem_ctx_size` entry spin at the reset. Core 0 was not in the synchronous-exception or IRQ marker, any earlier marker, `_panic_spin_forever` or the debugger trap path. That is consistent with the offline prediction. Several points come from the offline emulation, not from the device:

- `read_random` returned through the forwarding stub
- the caller was `vm_map_store_crypto_init`
- interrupts stayed masked, with no further device access

Next is supplying the corecrypto function table entries XNU needs, starting with the random-kmem entries backed by in-image code. The table layout will be mapped read-only first. Corecrypto services, interrupt handling and independent native return remain unproven.
