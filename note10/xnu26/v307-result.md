# v307 eight-CPU device-tree topology: pre-actor gate stopped

**No qualification; safe return.** Source `843e49aa42527cc4685c0434197169736cda8ece` built successfully in CI run `44749408572` after an earlier run of the previous commit stopped on a too-tight bound for the larger park-flow evidence log; that run is recorded as spent. The v307 kernel extends the device tree to twelve nodes with all eight CPU nodes and a `/chosen/memory-map`, checked at terminal entry by a 424-instruction stub.

The candidate kernel booted with CPUs 0-7 online. Before the actor, the host read the eight CPU node `reg` values from the candidate's device tree to precompute the expected device-tree hash. The values themselves matched the expected topology, but the host controller took their order from a multi-column directory listing, which is column-ordered, and so rejected them as out of order. The gate therefore stopped before the actor: no watchdog was opened, no park was requested and no record was expected.

The device returned to normal TWRP through the established fallback in a distinct boot epoch. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write and one host reboot; actor invocations, watchdog opens, RECOVERY writes, rollback BOOT writes and XNU executions were zero. The cycle is spent and will not be retried.

The ordering defect is in the host controller only. The next build carries the v307 entry checks forward with a corrected, order-independent topology read.
