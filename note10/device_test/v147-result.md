# v147 IVA deinit API errors: host result

The final global-init-reference path now returns a genuine negative synchronous PM API result through the existing DEINIT ioctl route. Private release helpers return integers; the global-reference edge uses the same refcount_dec_and_test primitive as the pinned native kref_put implementation. Last-reference status is a separate boolean. Nonnegative API results and inactive/nonfinal reference paths keep returning zero.

Reference consumption and existing PM/log ordering remain unchanged. There is no shared error slot, new mutex, reference rollback or retry. Native close keeps returning zero and completes the existing MCU, deinit, memory and process cleanup; forced iteration continues after errors. Task finalization remains after unlock.

The new GNU89 fixture passed 205 assertions with one transform, one refusal check, one compiler invocation and one fixture process. It exercises six authentic native bodies under PM and non-PM branches. Previously passed tests were not rerun.

The returned status identifies the synchronous API result only. It does not prove that a PM callback ran or establish DMA, firmware, clock or power state. This host result is separate from the prepared v146 four-object target compile and does not alter its frozen scope. No Image, package or device action occurred; the physical IVA owner gate remains closed.
