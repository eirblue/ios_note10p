# v304 terminal ABI record and watchdog return qualification

**Qualification PASS.** Source `7b41c5da3548390c839b2023e5904fbeba9368cb` built successfully in CI run `44555182258`. The compiled identity-map section was 2,120 bytes. Twelve new host-side parser and layout checks passed; earlier checks were not replayed.

Candidate TWRP booted the v304 kernel with CPUs 0-7 online. Before the actor ran, the host computed the expected entry `x0` independently: it read the kernel's own code and data resource ranges from `/proc/iomem`, required them to match the linked image spans, and added the linked offset of the diagnostic arena. The marker was not used to derive its own expectation.

The actor acknowledged the 10-second hardware watchdog with no keepalives. Sixteen checksummed records established that all eight online CPUs had reached the IRQ-disabled rendezvous. A subsequent 250-byte `N304PS2T` record, bound to the current build, diagnostic boot and cycle, showed entry at EL1 with SCTLR_EL1 M, C and I clear and all four DAIF mask bits set. Its `x0` equalled the precomputed arena address, `x1` and `x2` were zero, and its checksum was valid. The record survived into the recovered log after the rendezvous records.

Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, before the conservative software-return deadline. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot and one actor invocation. Watchdog-open and park-entry counts each had an upper bound of one. RECOVERY writes, rollback BOOT writes and XNU executions were zero.

The result qualifies the v304 terminal-entry register record and watchdog return. Raw reset cause, CPU power-off, independent native return and any XNU behaviour remain unproven.
