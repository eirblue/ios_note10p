# CPU0 local IRQ read-only observations

This optional diagnostic is default-off. Within the existing owned noirq CPU0 stop, it disables preemption, samples architecture, timer and GIC state, saves and masks local IRQs using the normal kernel API, samples again, restores the saved IRQ state, and takes a final sample before restoring preemption. CPU restoration remains mandatory on every failure. It adds no CPU hotplug operation, syscore callback, MMIO write or counter read. The six GICv2 register reads use the fixed distributor and CPU-interface addresses; non-banked GIC and unreviewed IRQ tracing or debug-snapshot configurations are rejected.

All three phases require CPU0 alone online with the expected IRQ and preemption state. The decoder requires two matching checksummed copies, exact IRQ restoration and local architecture/timer/GIC consistency; it also binds stable architecture and timer values to earlier CPU observations. TTBR1's address portion is cross-bound while its full value must remain equal across the local three phases. A failed or oversized observation produces bounded failure evidence and cannot pass. The existing GIC roundtrip propagates an error to the worker, preventing later observers from running after it fails.

The source, pinned kernel inputs, prepared helpers, build configuration, Image markers, actual-C synthetic models and decoder proofs are bound together. The models verify execution and failure cleanup under synthetic stubs; they do not establish hardware behavior. This observes no actual syscore execution, secure-world state or hardware DMA shutdown, and does not prove an XNU handoff or iOS boot.

## v34 physical result (2026-10-28)

Source `4cec79508c0bfaf09f12435b8ca6d981c0833f75` passed [kernel CI 40636741343](https://github.com/eirblue/ios_note10p/actions/runs/40636741343). One physical cycle passed all 29 evaluations. The CPU0 IRQ enabled, disabled and restored phases passed three-snapshot architecture, timer and read-only GIC comparisons; the original IRQ and CPU states were restored. Automatic TWRP return and all five post-test partition hash checks passed. Battery immediately before installation was 11%; 275 PC regression cases passed.

Whole-system DMA shutdown, actual syscore execution, MMU/cache handoff, XNU execution and iOS boot remain unverified.
