# Target-scoped GIC priority restoration

The default-off guard saves eight per-CPU SGI/PPI priority words during the existing GIC CPU-PM save and restores them on the paired exit or failed-entry notification. It retains the original fallback priority values when no valid paired snapshot exists, and preserves the original nonpriority restore sequence. A missing distributor or CPU interface invalidates a saved snapshot and preserves the original early return. Snapshot storage is per GIC and per CPU, allocated and initialized before notifier registration.

The supported configuration is one normally banked ARM GIC, with CPU-PM and the existing CPU-PM failure guard enabled. The supported runtime contract is the affected CPU with IRQs disabled and nonreentrant paired notifications. This change does not establish safety for nonbanked or secondary GIC configurations, arbitrary nested callbacks, FIQ/NMI mutation, hotplug or teardown.

Focused native tests execute the pinned original and final prepared GIC save, restore, notifier and initialization bodies with synthetic MMIO and allocation stubs. They compare original and feature-off traces, check the original four reads and eight additional priority reads, exercise the eight-word restoration and fallback, and test per-CPU/per-GIC isolation and allocation failures. Zero priority readback does not establish that a lane is implemented or writable.

The physical diagnostic retains the existing 37 evaluations and does not invoke CPU-PM or inject failures. PC models do not establish actual GIC hardware restoration, CPU-interface state preservation, global DMA shutdown, XNU execution or iOS boot.
