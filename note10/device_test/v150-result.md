# v150 duplicate IVA mailbox registration unlock

Duplicate registration in the native iva_mbox_callback_register function now reaches the existing common spin_unlock_irqrestore path before returning success. The duplicate remains a no-op: callback fields, list links and publication are unchanged. Invalid-input errors, descending priority order, stable equal-priority insertion, ordinary registration and existing unregister/RCU behavior are preserved. No new lock, IRQ-control, reset, power or witness action was added.

The new GNU89 fixture passed 156 assertions with one transform, one refusal check, one compiler invocation and one fixture process. It exercises the authentic native registrar body, including duplicate head and tail entries, fresh insertion after duplicates, invalid callbacks, priority insertion and restoration of modeled saved IRQ flags from enabled and disabled states. Previously passed tests were not rerun.

This host result models writer-lock ownership, saved IRQ flags and publication only. It does not establish actual IRQ, SMP or RCU execution, target kernel integration, shared SCORE mailbox closure, firmware or all-master DMA termination, or direct SFR mapping lifetime. No Image, package or device operation occurred; the physical IVA owner gate remains closed. XNU entry and complete boot are not established.

## Mailbox object CI

The single mailbox-object CI passed at source commit `a396cb6d079cc6ba47c4a1300bd06c4497b0aec0`: [run 42476803958](https://github.com/eirblue/ios_note10p/actions/runs/42476803958), job `128719871104`, attempt `1`. Exactly one requested target, `drivers/vision/iva/iva_mbox.o`, produced an AArch64 ELF64 little-endian relocatable object (165,920 bytes), SHA-256 `a2f065b7ad4bd20b692fc16ce0c2cc3ae19c55b9356765e52365434d085bb8e0`. The encrypted evidence was received, authenticated and safely extracted once; the authenticated producer result is PASS. Existing host PASS evidence was carried forward without rerunning host tests.

The mailbox compile records dependencies on `iva_mbox.h`, `iva_ctrl_ioctl.h`, `linux/interrupt.h`, `regs/iva_base_addr.h` and `regs/iva_mbox_reg.h`. The effective profile has ARM64, PM, EXYNOS_IVA and EXYNOS_IOVMM enabled, IVA version 30 and LTO disabled. `CONFIG_EXYNOS_IMA` is absent from the generated configuration and its generated macros are undefined; the mailbox object compiled under that profile.

This establishes the bounded mailbox target compile result only. No full kernel link, Image, package or device action occurred, and the physical IVA owner gate remains closed. Actual IRQ, SMP or RCU execution, shared SCORE mailbox closure, hardware power state, firmware or all-master DMA termination, direct SFR mapping lifetime, XNU entry and complete boot are not established.
