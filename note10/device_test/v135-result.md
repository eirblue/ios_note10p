# Note 10 v135 result

**Source:** `f9f1dc7e8f5520b5f9902c7c939b8dc87e3aaeed`  
**CI run:** `42141235541` passed  
**Scope:** native EVT1 SCORE shutdown reset and terminal handoff checks

## Host validation

The v135 new-only host checks passed. The first compiler launch was blocked before clang started by the sandbox; the remaining run compiled once and executed its fixture once. Previously passed checks were not replayed. The v135 CI build then passed once for the same source. No device operations occurred during host validation.

The package input path was corrected before generation, and the package was generated once without a retry. It consumed the retained compressed payload member once, read no raw kernel or adapter source, and performed no recompression. A reviewer also performed one unnecessary full hash read of the public TWRP reference. This caused no device change and is separate from the package producer required header read.

## Physical cycle

The cycle completed its one host BOOT write and one host reboot, then returned to fresh TWRP within the 240-second window. Integrity checks passed for all five tracked partitions.

The native handoff recorded its load and reboot markers and an `ENOENT` (`-2`) refusal at the NPU IOMMU-owner gate. The final hook was not observed. The bounded native SCORE provider shutdown/reset proof passed before the later NPU IOMMU-owner refusal. Overall handoff completion, XNU entry, a full XNU boot, and a watchdog reset cause remain unproven.

The cycle is spent and must not be replayed. The observed TWRP return and partition checks are recorded separately from proof of XNU execution.