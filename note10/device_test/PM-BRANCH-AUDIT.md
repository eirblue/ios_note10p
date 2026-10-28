# CPU-PM branch audit

The v38 diagnostic adds two default-off observations to the existing 35 evaluations. Under the existing chain lock it compares the PMU slot and EHLD event associations in memory and records the availability of reset, start and stop operations. It does not dereference the event object or invoke hardware or perf callbacks. The GIC priority-lane footprint is derived from existing observations without additional MMIO reads or writes.

PC validation binds the prepared source to the final build and exercises focused native source and synthetic models, including dispatch branches and caller restoration and error paths. These models use stubs and do not demonstrate that callbacks ran on the device. [CI 40724867871](https://github.com/eirblue/ios_note10p/actions/runs/40724867871) passed for source `736e14c97b634ad2f88e30c272a7d122043587e3`.

One physical diagnostic cycle passed all 37 evaluations. The battery immediately before installation was 81%; the device automatically returned to TWRP and all five partition integrity checks passed. After recovery, the TWRP and panel brightness settings both read raw 10.

The device observations showed a software PMU–EHLD association and a GIC priority-lane difference. These are observations, not evidence that CPU-PM execution or hardware restoration is safe. Actual CPU-PM invocation, XNU execution, iOS boot and global DMA shutdown were not verified.
