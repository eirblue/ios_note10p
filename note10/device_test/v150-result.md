# v150 duplicate IVA mailbox registration unlock

Duplicate registration in the native iva_mbox_callback_register function now reaches the existing common spin_unlock_irqrestore path before returning success. The duplicate remains a no-op: callback fields, list links and publication are unchanged. Invalid-input errors, descending priority order, stable equal-priority insertion, ordinary registration and existing unregister/RCU behavior are preserved. No new lock, IRQ-control, reset, power or witness action was added.

The new GNU89 fixture passed 156 assertions with one transform, one refusal check, one compiler invocation and one fixture process. It exercises the authentic native registrar body, including duplicate head and tail entries, fresh insertion after duplicates, invalid callbacks, priority insertion and restoration of modeled saved IRQ flags from enabled and disabled states. Previously passed tests were not rerun.

This host result models writer-lock ownership, saved IRQ flags and publication only. It does not establish actual IRQ, SMP or RCU execution, target kernel integration, shared SCORE mailbox closure, firmware or all-master DMA termination, or direct SFR mapping lifetime. No Image, package or device operation occurred; the physical IVA owner gate remains closed. XNU entry and complete boot are not established.
