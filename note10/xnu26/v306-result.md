# v306 multi-node device tree and CPU0 identity at entry

**Qualification PASS.** Source `b862ffa65e3dd8d1581165fe90221f6369c75e64` built successfully in CI run `44739259112`. The new host fixture passed 2 groups, 24 variants and 30 assertions, and thirty new host-side parser and expectation checks passed; earlier checks were not replayed. The diagnostic stub grew to 360 instructions under a raised 384-instruction bound, with the whole identity-map section still held within 4 KiB.

The Linux side now places a 428-byte XNU-encoded device tree with root, `/chosen` and `/cpus/cpu0` nodes inside the existing diagnostic arena, alongside the boot_args from v305. At terminal entry, with the MMU off, the stub walks that tree structurally with every access bounded to the tree, compares the cpu0 `reg` property with the live MPIDR_EL1 affinity and the `timebase-frequency` property with the live CNTFRQ_EL0, and checks that the boot_args video fields are zero. It records MPIDR_EL1 and ID_AA64MMFR0_EL1 read-only.

Before the actor ran, the host computed the expected entry `x0` from the kernel's `/proc/iomem` resources, read the cpu@0 `reg` and the timer frequency from the candidate's device tree, and from these computed the expected boot_args hash, boot-CPU affinity and device-tree hash; the device-tree model also uses the fixed 428-byte layout and the root compatible string identified from the v304 record. None of these expectations was derived from the record.

The actor acknowledged the 10-second hardware watchdog with no keepalives, and the checksummed rendezvous records established that all eight online CPUs had reached the IRQ-disabled stop. The subsequent 250-byte `N306PS2T` record, bound to the current build, boot and cycle, showed EL1 entry with SCTLR_EL1 M, C and I clear and all DAIF bits masked. Its `x0`, boot_args hash, device-tree hash and length, and recorded MPIDR affinity all matched the precomputed values exactly.

Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot and one actor invocation; RECOVERY writes, rollback BOOT writes and XNU executions were zero.

This qualifies a multi-node XNU-encoded device tree, consistent with the live boot-CPU identity and timer frequency, delivered intact to the terminal entry point. Raw reset cause, independent native return and any XNU behaviour remain unproven.
