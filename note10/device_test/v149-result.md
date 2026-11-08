# v149 failed IVA initialization state rollback

The existing clock-enable failure path in the native __iva_ctrl_init body now clears the INIT_DONE bit acquired by that call, after the existing error log and before returning the original negative error. Other state bits, successful initialization, already-initialized calls and the null-clock path are preserved. No clock-disable, power, IRQ, PM, lock or shared-error action was added.

The new GNU89 fixture passed 171 assertions with one transform, one refusal check, one compiler invocation and one fixture process. It exercises the authentic native initialization body with injected clock errors, a subsequent initialization call, successful initialization, preinitialized state and a null clock. Previously passed tests were not rerun. IMA and FPGA branches are disabled in this host fixture to match the selected profile.

This host result establishes software state rollback only. It does not establish target kernel integration, actual hardware clock or PM callback execution, power state, firmware or all-master DMA termination, shared SCORE mailbox closure or direct SFR mapping lifetime. No Image, package or device operation occurred; the physical IVA owner gate remains closed. XNU entry and complete boot are not established.
