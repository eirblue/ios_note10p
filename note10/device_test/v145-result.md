# v145 IVA file lifetime: host result

A separately owned binding and file context guard native process pointers across remove and rebind. Open uses device_trylock under the misc lock; other file operations use the parent device mutex. Remove detaches native pointers before existing teardown. Task and foreign-exporter finalizers run after unlocking. Binding cleanup under the core mutex is limited to sidecar free and a device reference drop proven non-final on the reviewed core paths.

The patch also balances misc deregistration after a successful registration followed by probe failure. Existing native hardware cleanup actions remain unchanged. The selected profile explicitly rejects enabled IMA and module builds; actual effective kernel configuration has not been observed.

The corrected GNU89 R2 host fixture passed 1,209 assertions, including probe failure, late file use, same-address rebind and a concurrent remove case using a Windows mutex model. It compiled and ran once, reusing the saved native transform. The original unused-global compilation failure is retained; R2 adds meaningful global publication/removal assertions without suppressing the warning. Native transformation ran once with two refusal checks; previously passed tests were not rerun.

This is an instrumented host result, not actual kernel integration or kernel VM execution. It does not revoke MMIO mappings or establish complete ION, DMA, firmware or shared-resource termination. No Image, package or device action occurred; the physical IVA owner gate remains closed.
