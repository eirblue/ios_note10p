# v153: idempotent IOMMU fault-notifier registration

The fresh diagnostic source registers at most one persistent fault notifier per existing master/SysMMU association. A private per-entry flag starts false through the existing zeroed allocation, is checked under the existing owner lock, and is set after the pinned notifier registration call. Every setter call still updates the handler/token pair. This avoids duplicate registrations on repeated set or stable-master driver rebind and prepares future callback rearm.

A partial allocation failure retains the original `-ENOMEM` and unlock behavior. Already registered entries keep their flags; a later retry allocates/registers only missing entries. Existing v152 coherent snapshots and token clear/RCU drain remain unchanged. The void public setter's error reporting and incomplete coverage after partial allocation failure are not changed.

New host batch: **PASS, 88 assertions**, one compiler invocation and one fixture process, zero old tests replayed. These deterministic software models are not real IRQ/RCU/SMP execution.

Native CI: **PASS**, compiled exactly one provider object, `drivers/iommu/exynos-iommu.o`. The one artifact receive used GET, original Node OPEN, and safe extraction once each. The receiver initially rejected the artifact because its carried nested workflow hash was stale; the original receive terminal remains **failed-spent-no-retry**. A metadata-only reconciliation independently verified the producer PASS and exact dispatch context; only the workflow hash in the nested operator/receiver orchestration maps differed. No re-download, rebuild, or retry occurred.

Physical readiness remains false. No device action or physical cycle occurred; hardware DMA quiescence, physical owner success, and XNU/iOS execution remain unproven. Normal MCU/PM callback-resource gating and persistent record retirement/platform-device destruction also remain unproven.
