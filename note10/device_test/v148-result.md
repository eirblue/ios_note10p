# v148 failed IVA PM initialization accounting

The existing first-global-init failure branch now balances the PM usage reference acquired by pm_runtime_get_sync with one pm_runtime_put_noidle call under CONFIG_PM. It preserves the existing log, process-reference reset and original negative error return. Non-PM failures and valid initialization/reference paths are unchanged.

The no-idle primitive only balances software usage accounting. The patch adds no idle, suspend, deinit, retry or runtime-status override and makes no hardware rollback claim.

The new GNU89 fixture passed 169 assertions with one transform, one refusal check, one compiler invocation and one fixture process. It exercises the authentic initialization body in PM and non-PM variants. Previously passed tests were not rerun.

This host-only result does not establish target kernel integration, PM callback execution, power state, DMA termination or IVA ownership. It is outside the frozen v146 and v147 CI scopes. No Image, package or device operation occurred.

## Target object CI

The single controller-object CI passed at source commit `6ef0f3992f2a709039e1d4b642a5157d941b0db0`: [run 42473621760](https://github.com/eirblue/ios_note10p/actions/runs/42473621760), job `128709954360`, attempt `1`. Exactly one requested target, `drivers/vision/iva/iva_ctrl.o`, produced an AArch64 ELF64 little-endian relocatable object (279,152 bytes), SHA-256 `c70b1a4ef1494077a541a9194c45f99e05d5e32f2e5c8a546b289fc9c0f8d767`. The encrypted evidence was received, authenticated and safely extracted once; the authenticated producer result is PASS. Existing host PASS evidence was carried forward without rerunning host tests.

The effective profile has ARM64, PM, EXYNOS_IVA and EXYNOS_IOVMM enabled, IVA version 30 and LTO disabled. The IMA check is resolved: `CONFIG_EXYNOS_IMA` is absent from the generated configuration, its generated macros are undefined, and the production sidecar fence compiled. This establishes the bounded target compile result only. No full kernel link, Image, package or device action occurred, and the physical IVA owner gate remains closed. PM callback execution, hardware power state, DMA or firmware termination, XNU entry and complete boot are not established.
