# v303 EL1 MMU-off watchdog return qualification

**Qualification PASS.** Source `9de74368588649fe13632a2b40d2d3074e6ed555` built successfully in CI run `44265652807`. The source-bound host fixture passed 2 groups, 17 variants and 17 assertions. Separate host-side parser and qualification checks passed 12 cases. The compiled identity-map section was 1,400 bytes, and the diagnostic stub was 252 bytes.

Candidate TWRP and its PID 1 passed the lifecycle admission checks. The actor acknowledged the 10-second hardware watchdog with no keepalives, and 16 checksummed records established that all eight online CPUs had reached the IRQ-disabled rendezvous. A subsequent 250-byte record tied to the current build, diagnostic boot and cycle showed that the diagnostic stub had reached EL1 with the SCTLR_EL1 M, C and I bits clear. The record had a valid checksum and append-cursor advance and survived into the recovered log.

Normal TWRP returned in a distinct boot epoch 56.8 seconds after the actor started, before the conservative software-return deadline. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot and one actor invocation. The watchdog-open and park-entry counts each had an upper bound of one. RECOVERY writes, rollback BOOT writes and XNU executions were zero.

The result qualifies watchdog return from the diagnostic stub after the EL1 MMU-off transition. The post-entry design relied on the armed hardware watchdog. Raw reset cause, CPU power-off and independent native return remain unproven.
