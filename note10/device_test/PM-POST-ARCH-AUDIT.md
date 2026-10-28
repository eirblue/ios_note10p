# Post-PM per-CPU architecture and payload observations

The v31 physical diagnostic passed its 22 individually reported evaluations.
This default-off extension adds post-PM architecture comparison and payload
readback across all eight CPUs to the existing diagnostic. It runs only after
successful PM restoration, the existing GIC test, and payload SHA checks.

Each callback reads the current EL, MPIDR, SCTLR, TCR, TTBR1 and MAIR and
reads the staged payload using the existing full-word fingerprint function.
The online set is held under the normal CPU read lock. It is checked before
and after synchronous callbacks; missing, duplicate or unexpected CPUs fail.
The worker repeats SHA256 after all callbacks. The fingerprint supplements,
but does not replace, the staged payload's SHA256 identity check.

Each CPU is compared with its own earlier CPU/cache snapshot. TTBR1 bits
63:48 are excluded because the pinned kernel uses them for the active ASID;
the remaining bits must match. No register write, extra CPU hotplug, device
PM request, cache maintenance or extra peripheral register access is added.
The producer emits two separate checksummed evidence lanes, tied to the same
completed PM generation and build identity. The collector compares the
frames to the earlier verified snapshots and requires both lanes to pass.

The native model executes the actual observer with injected per-CPU faults,
including an ASID-only change, and exercises the prepared PM worker's error
branches. These are PC models, not evidence of physical operation. Results
do not establish global DMA shutdown, GIC/MMU/cache handoff or XNU execution.

## v32 physical result, 2026-10-28

Source `85f82519c2d04d17a00de12e8a2d80b73a3fe1e2` and
[CI 40624098218](https://github.com/eirblue/ios_note10p/actions/runs/40624098218)
passed. PC verification passed 275 regression tests, 37 actual observer C
fault cases, and eight prepared-worker cases. One fresh physical diagnostic
passed all 24 individually reported evaluations.

All eight CPUs passed the post-PM architecture comparison and the separate
full-payload readback check. The original payload SHA256 check also passed.
Automatic TWRP return and all five post-test partition integrity checks passed.
Battery was 21% immediately before installation. Device logs, register values,
identifiers, backups and device images remain private.

These observations are limited to this single diagnostic roundtrip. They do
not establish complete DMA shutdown, hardware GIC/MMU/cache handoff, XNU
execution or iOS boot.
