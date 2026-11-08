# v153: idempotent IOMMU fault-notifier registration

The fresh diagnostic source registers at most one persistent fault notifier per existing master/SysMMU association. A private per-entry flag starts false through the existing zeroed allocation, is checked under the existing owner lock, and is set after the pinned notifier registration call. Every setter call still updates the handler/token pair. This avoids duplicate registrations on repeated set or stable-master driver rebind and prepares future callback rearm.

A partial allocation failure retains the original `-ENOMEM` and unlock behavior. Already registered entries keep their flags; a later retry allocates/registers only missing entries. Existing v152 coherent snapshots and token clear/RCU drain remain unchanged. The void public setter's error reporting and incomplete coverage after partial allocation failure are not changed.

New host batch: **PASS, 88 assertions**, one compiler invocation and one fixture process, zero old tests replayed. The authentic registrar and changed private struct are checked with first/repeated registration, replacement pairs, partial allocation failure/retry, clear/rearm model state, and lock/counter checks. These are deterministic software models, not real IRQ/RCU/SMP execution.

Native ARM64 compilation of the single modified IOMMU unit is pending. Normal MCU/PM callback-resource gating, persistent record retirement/platform-device destruction, hardware DMA quiescence, physical owner success and XNU/iOS boot remain unproved. No Image or device operation is part of this result.
