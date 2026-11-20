# v312 XNU entry target located and read at entry

**Qualification PASS.** Source `298132b6c2d464ee2608c48e63828c488f217846` built successfully in CI run `44802987801`. The new v312 fixture (4 groups, 26 variants, 26 assertions) passed; earlier checks were not replayed. The stub grew from 553 to 566 instructions, within the 640-instruction self-imposed bound, and the whole identity map stayed within 4096 bytes.

v312 locates the XNU kernel entry point without branching to it. After loading the pinned XNU image into the reserved window, as in v311, the candidate Linux kernel parses the image's Mach-O load commands with every read bounds-checked. It requires exactly one `LC_UNIXTHREAD` whose program counter lies inside an executable segment of the loaded image, and stores the entry offset for the stub. Any parse failure stops before the CPUs are quiesced, with no record. The host parses the same pinned image independently.

At terminal entry, with SCTLR_EL1 M, C and I clear, the stub ran all of the v311 checks, including the whole-image hash, then confirmed that the entry offset is nonzero, 4-byte aligned and inside the image, and loaded the instruction word at the entry point. It never branches to it. The `N312PS2T` record, bound to the current build, boot and cycle, matched the precomputed `x0`, boot_args hash, device-tree hash, node count and image hash, and its entry slot matched the host-parsed entry offset and instruction word exactly.

Normal TWRP returned in a distinct boot epoch. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot and one actor invocation; RECOVERY writes, rollback BOOT writes, XNU executions and entry branches were zero.

This qualifies the XNU entry target, resident and intact in the reserved window and agreeing between the device and the host, at the terminal entry point. Raw reset cause, independent native return and any XNU behaviour remain unproven.
