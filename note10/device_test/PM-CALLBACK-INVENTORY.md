# PM callback metadata inventory

This optional diagnostic is default-off. The existing maximum compatible profile enables it automatically. It adds four required evaluations to the previous 29: CPU-PM notifier, generic IRQ chip, clocksource and clockevent metadata. Each family is observed at the existing pre-PM eight-CPU, CPU0-only and post-PM eight-CPU points, without an additional PM or CPU hotplug cycle.

The inventory records possible registered paths; it does not execute callbacks. Generic IRQ callback eligibility that depends on irq_data remains unknown. Clockevent list order can change between phases, and membership locking does not make remote per-CPU state observations simultaneous. Identical symbol names can represent distinct builtin addresses: internal IDs are assigned by address while raw addresses are never printed.

Output is bounded to 128 KiB including two checksummed copies and line overhead. The enabled profile sets `CONFIG_LOG_BUF_SHIFT=21`; capacity, symbol or output overflow fails explicitly. A bounded output budget does not guarantee future kernel-log retention.

No v35 full-kernel CI or physical-device result has yet been obtained. Raw per-device callback lists, names and observations remain private. This diagnostic does not establish whole-system DMA shutdown, syscore execution, MMU/cache handoff, XNU execution or iOS boot.
