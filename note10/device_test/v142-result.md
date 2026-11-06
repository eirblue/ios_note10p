# v142 IVA firmware-argument result

A PC-only NEW test batch passed 20 cases using the authentic native IVA boot-function bodies. Copy faults preserved `-EFAULT`; empty, wrong, overlong, unterminated, and NULL firmware arguments were rejected before reference, QoS, file, or boot actions. Valid-path behavior, cleanup ordering, and uninitialized-device `-EIO` precedence passed.

The batch applied one transform, compiled once, and ran one fixture. No existing tests were replayed. Kernel CI and device operations were both zero. The result does not establish kernel integration, firmware execution, DMA-idle, physical power-off, or IVA owner safety.

Callback errno propagation, VDMA and lifecycle tracking, and terminal predicates remain unresolved. The v141 physical cycle remains spent; v142 adds no physical action or IVA owner promotion.
