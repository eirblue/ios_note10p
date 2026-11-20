# v310 /defaults device-tree node at entry

**Qualification PASS.** Source `9ca850525ba1050bf0ddde79b957222232c48515` built successfully in CI run `44779635081`. The new v310 fixture (3 groups, 53 variants, 61 assertions) passed; earlier checks were not replayed. The stub grew from 469 to 502 instructions, within the 512-instruction self-imposed bound, and the whole identity map stayed within 4096 bytes.

v310 appends an empty root `/defaults` node, carrying only its `name` property, as the last node of the XNU-encoded device tree. XNU development kernels assert that this node exists during early pmap bootstrap. Because the node is appended last, every v309 value offset is unchanged; the tree grows by 56 bytes to a fixed 13-node layout. No reservation, load address, CPU, MMIO or MMU behaviour changed.

As in v309, the host controller ran the read-only CPU topology and `/proc/iomem` DRAM-span checks in normal TWRP before any write, and on the candidate before the actor, and computed the expected boot_args and device-tree hashes from host-side facts only.

At terminal entry, with SCTLR_EL1 M, C and I clear, the stub ran all of the v309 checks, then confirmed that the root has three children and that a `/defaults` node with one property and no children ends exactly at the device-tree length, before committing. The `N310PS2T` record, bound to the current build, boot and cycle, matched the precomputed `x0`, boot_args hash, device-tree hash and node count exactly, and its dram-size slot again equalled the host-derived span size.

Normal TWRP returned in a distinct boot epoch. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot and one actor invocation; RECOVERY writes, rollback BOOT writes and XNU executions were zero.

This completes the description-only device-tree content the early XNU path requires, delivered intact to the terminal entry point. Raw reset cause, independent native return and any XNU behaviour remain unproven.
