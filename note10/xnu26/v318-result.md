# v318 XNU passes its memory-configuration check and stops at the next VM bootstrap dependency

**Qualification PASS.** Source `df1561d51ca01f92d4666496599af01b93a5597a` built successfully on the first attempt in CI run `44947191494`. The new v318 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v317 contract body, the v316 stub and the v316 Linux code were reused unchanged, and the stub stays at 617 instructions. The only public change is the record tag `N318PS20`, so the cycle ran a new reviewed build and no spent build was replayed. The independent source review rejected the first revision for two defects in private host scripts and accepted the corrected revision.

In v317 core 0 stopped at the marked `arm_vm_init` memory-configuration rejection. Offline static analysis of the pinned image then showed that this check does not depend on the memory size. It compares the kernel virtual address of `topOfKernelData` against a fixed limit. Because the image is not rebased, XNU's virtual base is tied to its link address, and every legal `topOfKernelData` maps above that limit. No boot_args value and no larger reservation can satisfy the check.

v318 bundles a minimal private image patch on top of the v317 marked image:

- The memory-configuration check is skipped.
- XNU's initial page-table pass (`init_ptpages`) now stops when its address wraps past the top of the 64-bit space. Without this, offline emulation showed the very next step wrapping and exhausting XNU's page allocator.
- Two new markers turn the cold-path entries of the illegal-physical-address panic and of page-allocator exhaustion into distinct self-spins. The four v317 markers remain.
- boot_args, the device tree, the seed, the handoff layout, the stub and the Linux code are identical to v317. The patch itself performs no MMIO access, system-register write or CPU bring-up; it lets XNU continue building its own page tables, and in the offline emulation no translation-table or translation-control register was written before the stop.
- Before use, an offline check emulated the patched image. XNU passed the skipped check, the page-table pass ended at the wrap, and execution stopped at the illegal-physical-address marker after reading an empty top-level page-table slot.

On the device, the stub ran every check, committed the `N318PS2T` record and branched to XNU. The record, bound to the current build, boot and cycle, matched the precomputed values exactly.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the illegal-physical-address marker spin, as predicted. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

This qualifies the patch as far as the marker shows. The program counter identifies which marked spin core 0 was in at the reset, and nothing more. Core 0 was at the illegal-physical-address site, not at the memory-configuration, page-allocator, or seed markers, and not in `_panic_spin_forever`. That is consistent with the offline prediction: XNU got past the skipped check and the wrap fix, then read an empty top-level page-table slot. The marker does not show which code ran in between, or the contents of the tables XNU built.

The analysis points to the underlying cause. This XNU expects its static kernel in a lower region of the kernel address space than the one the image is linked at, so further patching of the VM bootstrap would likely keep finding new stops. Next is a read-only assessment of relinking the kernel at the expected base. XNU progress past the VM bootstrap and independent native return remain unproven.
