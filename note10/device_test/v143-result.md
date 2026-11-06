# v143 IVA timer lifetime: host result

The native IPC timer producer now checks lifecycle state under an IRQ-safe lock. Init, deinit and remove are serialized; closing the timer precedes synchronous timer drain, with no state spinlock held across the drain. Only successful init reopens it, and remove is permanent.

The new GNU89 native-body fixture passed 23 cases with one transform, one compiler invocation and one fixture process. Previously passed tests were not rerun. Two documented host pointer-width bridges leave target source ABI unchanged.

This result covers software timer lifetime. Actual AArch64 kernel integration, file lifetime, DMA and firmware termination remain unproven. No Image, package or device action occurred; the physical IVA owner gate remains closed.
