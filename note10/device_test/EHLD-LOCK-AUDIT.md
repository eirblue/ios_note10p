# CPU0 EHLD lock availability audit

The v45 default-off `CONFIG_NOTE10_EHLD_LOCK_AUDIT` audit extends the existing owned CPU0, IRQ-disabled, non-interrupt notifier walk. It checks the exact EHLD notifier and callback before resolving the static per-CPU control object, then attempts its raw spinlock once. A busy lock is a valid observation with no running-field read and no unlock. On success, the audit reads the running field once, reports its boolean value, and releases the acquired lock before leaving the node. An error after acquisition also releases the lock.

The preceding EHLD observation retains its signed integer value. The new audit checks that value's range and identity before comparing boolean values; negative nonzero values remain true. Final chain count and lifecycle checks bind the observation to the completed walk. The output contains normalized lock/running fields and chain identity, without pointers or raw hardware registers.

These separate observations are not an atomic snapshot or a promise of future lock availability. The control lock does not protect performance-event lifetime, and the audit does not dereference an event, its attributes, or ring-buffer metadata. Existing CPU0 task and IRQ serialization assumptions still apply. No CPU-PM callback, PMU operation, state repair, or hardware restoration is introduced.

The bundled diagnostic profile requests dynamic probe and function-tracing options off, including the derived BPF-events option, while preserving EHLD, perf, preemption, RCU, static tracepoints, tracing, and debug snapshot support. Effective kernel configuration must be checked after configuration resolution; this is not a claim that all instrumentation is absent.

Source composition, synthetic native models, and decoder tests do not establish kernel ABI compatibility or device success. Actual kernel compilation and a separately reviewed physical cycle are required. No v45 physical result is recorded here yet. XNU execution, iOS boot, global DMA quiescence, and complete hardware restoration remain unestablished.
