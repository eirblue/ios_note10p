# Note 10 v137 result

**CI run:** `42167875513` passed  
**Scope:** native CAL macro correction and typed terminal witnesses for SCORE, G2D, and NPU

## Host validation

The v137 new-only synthetic check passed with one compile and one fixture run; earlier tests were not replayed. The CI build passed once. The package was generated once, consuming the retained compressed payload member once with no raw kernel or adapter reads and no recompression.

## Physical cycle

The cycle used one BOOT write and one host reboot, then returned to fresh TWRP within the 240-second limit. Integrity checks passed for all five tracked partitions. The native handoff recorded one load and one reboot marker.

Typed per-owner terminal witnesses passed for SCORE domain-off, cold NPU both-domain-off, and G2D domain-off. These records do not establish physical clock-off or that every DMA master is inactive. The handoff then reported an `ENOENT` (`-2`) refusal at the DisplayPort IOMMU-owner gate.

XNU entry, a full XNU boot, and a watchdog reset cause remain unproven. The cycle is spent and must not be replayed.