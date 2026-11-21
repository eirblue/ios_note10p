# v314 first breadcrumb from inside the loaded XNU image

**Qualification PASS.** Source `e7e0ba648360bccd823afb537cf3bd5ad3b380fc` built successfully in CI run `44910396137`. The new v314 fixture (4 groups, 19 variants, 19 assertions) passed; earlier checks were not replayed. The stub kept v313's 597 instructions, and the only change widened one cache-clean bound to cover the record plus 16 breadcrumb bytes. The whole identity map stayed within 4096 bytes.

v314 asks how far XNU runs after the v313 branch. Before loading, a private host-side step patched the pinned XNU image in two places, each redirected to a small hook in an unused zero region of the image's executable text:

- the entry instruction
- the instruction just before XNU first enables its MMU

Each hook appends one 8-byte breadcrumb to the kernel log right after the v314 record. A hook writes only if the log's write cursor sits exactly at its expected position: the end of the record for the first breadcrumb, the end of the first breadcrumb for the second. It never touches MMIO or system registers, then resumes the original instruction stream. An offline check disassembled and emulated the patched image before use. The patched image itself stays private.

On the device, the stub ran every v313 check against the patched image, committed the `N314PS2T` record and branched to XNU with `x0` set to the boot_args address, as in v313. The record, bound to the current build, boot and cycle, matched the precomputed values and the patched entry word exactly.

After the reset, the log read back from the previous boot showed the first breadcrumb directly after the record, but not the second. The boot loader's next log block reported a cluster-0 watchdog reset. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

This is the first direct evidence that code inside the loaded XNU image executed on this device: the patched entry branch and the injected entry hook ran and wrote the first breadcrumb. Execution of XNU's own unmodified instructions after the hook is not proven. The second breadcrumb is absent. Either XNU stopped between its entry and its first MMU enable, or the second hook's write guard did not match; this build cannot tell which. The reset was a watchdog reset, as designed. XNU progress past entry and independent native return remain unproven.
