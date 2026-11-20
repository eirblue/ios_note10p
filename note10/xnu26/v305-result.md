# v305 boot_args CommandLine and field adjudication

**Qualification PASS.** Source `fd9a464ff755e364f614b26bcedf193380d53355` built successfully in CI run `44732188990`, including the first gcc `-Wall -Wextra -Werror` build of the new boot_args fixture. Fifteen new host-side parser and expectation checks passed; earlier checks were not replayed.

The 1,152-byte XNU-style boot_args now carries a non-empty CommandLine, `-v n10diag=305`. At terminal entry the diagnostic stub performs read-only checks of the boot_args fields before committing its record: virtual and physical base equal the arena, memory size and top-of-kernel-data agree, machine type and boot flags are zero, actual memory size is at least the arena size, and the CommandLine is NUL-terminated printable ASCII.

Before the actor ran, the host computed the expected entry `x0` from the kernel's `/proc/iomem` resources and the linked arena offset, then computed the expected boot_args hash from that address and the CommandLine. The expected device-tree hash and length come from a fixed model of the synthetic device tree, whose root compatible string was identified from the v304 record. Neither expectation was derived from this record.

The actor acknowledged the 10-second hardware watchdog with no keepalives, and the checksummed rendezvous records established that all eight online CPUs had reached the IRQ-disabled stop. The subsequent 250-byte record, bound to the current build, boot and cycle, showed EL1 entry with SCTLR_EL1 M, C and I clear and all DAIF bits masked. Its `x0`, boot_args hash, device-tree hash and length all matched the precomputed values exactly, so the new field checks passed on hardware.

Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot and one actor invocation; RECOVERY writes, rollback BOOT writes and XNU executions were zero.

This qualifies an XNU-style boot_args with a CommandLine, delivered intact to the terminal entry point. Raw reset cause, independent native return and any XNU behaviour remain unproven.
