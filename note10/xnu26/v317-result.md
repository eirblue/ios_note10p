# v317 XNU accepts the boot random seed and reaches its memory-configuration check

**Qualification PASS.** Source `45a7d1ddb0e8dd5b6246e925cafd0e737bac5a51` built successfully on the first attempt in CI run `44939763814`. The new v317 fixture (6 groups, 20 variants, 20 assertions) passed; earlier checks were not replayed. The v316 stub and Linux code were reused byte-identical. The stub's only assembled difference is the larger device-tree size bound, and it stays at 617 instructions, within the 640-instruction self-imposed bound.

In v316 XNU ran past its first MMU enable and core 0 stopped in `_panic_spin_forever`. Offline emulation put that stop at the panic for the missing random seed. The device program counter alone could not tell which panic had fired, because every panic ends in the same spin.

v317 bundles the fix and a way to tell the stops apart:

- The device tree's `/chosen` node gains a `random-seed` property of exactly 256 bytes. Its value is a fixed public synthetic pattern with no zero byte. It contains nothing device-derived or secret. This is a diagnostic boot, so nothing relies on XNU's early entropy, and the predictability of that entropy is accepted.
- The device-tree storage and size limit grow from 2048 to 4096 bytes. The arena and the handoff copy still fit their 16 KiB pages. The contract tag becomes `N317PS20`. The handoff layout, breadcrumbs, stub and Linux code are otherwise unchanged from v316.
- A private host-side step marked four XNU panic sites on this path in the pinned image, so that each stops in its own self-spin instead of calling the panic routine. The sites are:
  - the `arm_vm_init` memory-configuration rejection (the predicted stop)
  - the missing random seed (the v316 stop)
  - a wrong seed length
  - a failed random-generator initialization

  Any other panic still ends in `_panic_spin_forever`, which therefore no longer means the v316 panic. Nothing else in the image changed.
- Before use, an offline check emulated the marked image with the v317 device tree. XNU passed early random initialization and stopped at the memory-configuration marker.

On the device, the stub ran every check, committed the `N317PS2T` record and branched to XNU. The record, bound to the current build, boot and cycle, matched the precomputed values exactly. It covers the device tree including the seed.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the memory-configuration marker spin, as predicted. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

This qualifies the fix as far as the marker shows. The program counter identifies which marked spin core 0 was in at the reset, and nothing more. Core 0 was at the memory-configuration site, not at any of the three seed-related markers or in `_panic_spin_forever`. That is consistent with the seed being accepted and XNU reaching `arm_vm_init`'s memory-configuration check, as the offline prediction says. The marker does not show which code ran in between, or that any later step would succeed. Handling the memory-configuration rejection is the next step. XNU progress past `arm_vm_init` and independent native return remain unproven.
