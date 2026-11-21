# v315 XNU reaches the instruction before its first MMU enable

**Qualification PASS.** Source `5aa10d81959949334da981c65f94cd2c99a2f208` built successfully in CI run `44916359275`. The new v315 fixture (7 groups, 32 variants, 32 assertions) passed; earlier checks were not replayed. The stub grew from 597 to 599 instructions, within the 640-instruction self-imposed bound, and the whole identity map stayed within 4096 bytes.

In v314 the first breadcrumb appeared and the second did not. Offline static analysis and emulation of the pinned XNU image then found why. XNU's early bootstrap page-table builder refuses a mapping larger than 32 MiB, and the memory size passed in boot_args was larger. So the builder returned an error and XNU stopped in its own error loop before enabling the MMU, until the watchdog fired. Emulating with the v314 value reproduced exactly this stop.

v315 bundles the fix and its check:

- The boot_args memory size is now the kernel offset plus 32 MiB, a new contract constant. The stub checks the image against it. The reserved window and the actual memory size are unchanged.
- A private host-side step patched the pinned image with three hooks:
  - at the entry point
  - right after the bootstrap builder returns, recording its return code as one hex digit
  - just before XNU's first SCTLR write that enables the MMU
- Each hook finds the kernel log from its own position in the image, so it needs no register or host-supplied address. It appends one 8-byte breadcrumb only if the log's write cursor sits within the expected range. It touches no MMIO or system registers, and then resumes the original instruction stream.
- Before use, an offline check disassembled the patched image and emulated it with the v315 boot_args. The builder returned 0 and execution reached the SCTLR write.

On the device, the stub ran every check, committed the `N315PS2T` record and branched to XNU, as in v314. The record, bound to the current build, boot and cycle, matched the precomputed values exactly.

After the reset, the log read back from the previous boot held all three breadcrumbs, in order, directly after the record. The builder code was 0, exactly as predicted. The boot loader's next log block reported a cluster-0 watchdog reset. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

This qualifies the fix. With the corrected memory size, XNU's bootstrap page-table builder succeeds, and execution reaches the instruction before XNU's first MMU enable. Nothing after the MMU enable was observable. The boot_args and device tree currently lie outside XNU's early 32 MiB mapping, so a stop shortly after the MMU enable is expected; moving them is the next step. XNU progress after the MMU enable and independent native return remain unproven.
