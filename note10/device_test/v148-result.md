# v148 failed IVA PM initialization accounting

The existing first-global-init failure branch now balances the PM usage reference acquired by pm_runtime_get_sync with one pm_runtime_put_noidle call under CONFIG_PM. It preserves the existing log, process-reference reset and original negative error return. Non-PM failures and valid initialization/reference paths are unchanged.

The no-idle primitive only balances software usage accounting. The patch adds no idle, suspend, deinit, retry or runtime-status override and makes no hardware rollback claim.

The new GNU89 fixture passed 169 assertions with one transform, one refusal check, one compiler invocation and one fixture process. It exercises the authentic initialization body in PM and non-PM variants. Previously passed tests were not rerun.

This host-only result does not establish target kernel integration, PM callback execution, power state, DMA termination or IVA ownership. It is outside the frozen v146 and v147 CI scopes. No Image, package or device operation occurred.
