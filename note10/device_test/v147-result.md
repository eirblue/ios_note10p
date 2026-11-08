# v147 IVA deinit API errors: host result

The final global-init-reference path now returns a genuine negative synchronous PM API result through the existing DEINIT ioctl route. Private release helpers return integers; the global-reference edge uses the same refcount_dec_and_test primitive as the pinned native kref_put implementation. Last-reference status is a separate boolean. Nonnegative API results and inactive/nonfinal reference paths keep returning zero.

Reference consumption and existing PM/log ordering remain unchanged. There is no shared error slot, new mutex, reference rollback or retry. Native close keeps returning zero and completes the existing MCU, deinit, memory and process cleanup; forced iteration continues after errors. Task finalization remains after unlock.

The new GNU89 fixture passed 205 assertions with one transform, one refusal check, one compiler invocation and one fixture process. It exercises six authentic native bodies under PM and non-PM branches. Previously passed tests were not rerun.

The returned status identifies the synchronous API result only. It does not prove that a PM callback ran or establish DMA, firmware, clock or power state. This host result is separate from the prepared v146 four-object target compile and does not alter its frozen scope. No Image, package or device action occurred; the physical IVA owner gate remains closed.

## Target object CI

The single controller-object CI passed at source commit `e7dee651a97dc5d74db591ed098a324f1827ef4b`: [run 42472633787](https://github.com/eirblue/ios_note10p/actions/runs/42472633787), job `128706787742`, attempt `1`. Exactly one requested target, `drivers/vision/iva/iva_ctrl.o`, produced an AArch64 ELF64 little-endian relocatable object (276,048 bytes), SHA-256 `0362e35d1b25f57797493ebe00d53850bc3293bab5a37d5705a1e3fccf339b90`. The encrypted evidence was received, authenticated and safely extracted once; the authenticated producer result is PASS. Existing host PASS evidence was carried forward without rerunning host tests.

The effective IMA check is resolved: `CONFIG_EXYNOS_IMA` is absent from the generated configuration, its generated macros are undefined, and the production sidecar fence compiled. This establishes the bounded target compile result only. No Image, package or device action occurred, and the physical IVA owner gate remains closed. PM callback execution, DMA or firmware termination, XNU entry and complete boot are not established.
