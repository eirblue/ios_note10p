# v309 /chosen dram-base and dram-size at entry

**Qualification PASS.** Source `03363d7ed0d6016fe0b475e6282cf32e5ae71c1e` built successfully in CI run `44765663204`. The new v309 fixture (3 groups, 40 variants, 47 assertions) passed; earlier checks were not replayed. The stub grew from 424 to 469 instructions, within the raised 512-instruction self-imposed bound, and the whole identity map stayed within 4096 bytes.

v309 adds the last two `/chosen` properties that early XNU `arm_init` requires, `dram-base` and `dram-size`, each a little-endian 64-bit value. The kernel derives them from the Linux memblock DRAM start and end. The XNU-encoded device tree grows by 88 bytes to a fixed 12-node layout; no reservation, load address, CPU, MMIO or MMU behaviour changed.

Before any write, the host controller parsed the top-level `System RAM` and `reserved` resources of `/proc/iomem` once, read-only, in normal TWRP. A parse fault there would have stopped the cycle with nothing spent. On the candidate, before the actor, the host derived the expected DRAM span from the candidate's own `/proc/iomem`, required the entry arena to lie inside one `System RAM` resource and the span to match the previous build's, and computed the expected boot_args and device-tree hashes from it. None of these expectations was derived from the record.

At terminal entry, with the MMU off, the stub ran all of the v308 checks. It then confirmed that both new properties have 8-byte values and the expected names, that the size is nonzero and does not wrap, and that the span contains the 16 KiB entry arena, before committing. The `N309PS2T` record, bound to the current build, boot and cycle, matched the precomputed `x0`, boot_args hash, device-tree hash and node count exactly. Its dram-size slot also equalled the host-derived span size exactly.

Normal TWRP returned in a distinct boot epoch. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot and one actor invocation; RECOVERY writes, rollback BOOT writes and XNU executions were zero.

This qualifies the complete early-XNU `/chosen` DRAM description, delivered intact and self-consistent to the terminal entry point. Raw reset cause, independent native return and any XNU behaviour remain unproven.
