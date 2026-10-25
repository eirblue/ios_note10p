# CPU offline/online and cached readback diagnostic

This opt-in batch runs after the same-boot reservation, full RAM patterns and
verified experimental XNU data staging. Failed prerequisites stop later phases.
It is prepared for a human-installed temporary BOOT diagnostic.

1. Require Linux logical CPUs 0–7 online and verify the staged payload SHA256.
2. Use the pinned Linux `disable_nonboot_cpus()` implementation. Require only
   Linux CPU 0 online. No MPIDR/PSCI mapping is inferred or supplied by the host.
3. Clean/invalidate the payload range with the arm64 Linux cache primitive and
   issue a barrier. Compare the SHA256 again while secondary CPUs are offline.
4. Call `enable_nonboot_cpus()` after every freeze attempt, including errors.
   Require the original online set to be restored.
5. Hold the CPU read lock during synchronous callbacks. Each of eight logical
   CPUs reads every payload word and records a supplementary 64-bit fingerprint,
   CurrentEL, MPIDR, SCTLR, TCR, TTBR1, MAIR and timer registers. Require matching
   reads, EL1, normal Linux caches/MMU enabled and a 26MHz counter. Finish with
   another SHA256 check on the primary CPU.

Checksummed N10HOP1 checkpoints locate interrupted phases. Success requires two
distinct N10QUI1 summaries and two agreeing N10CPU2 snapshots from every CPU,
plus the existing same-boot RAM and XNU staging evidence. Snapshots retain MPIDR
aliases; they do not invent unique affinity IDs. Raw addresses/registers stay in
private captures. The collector rejects merged intervals and corrupted evidence.

The actual C is executed in PC RAM with modeled CPU/cache/register APIs and real
SHA256. Fault cases cover early refusals, partial/failed freezes, mandatory
restoration, cache/readback faults, missing/duplicate callbacks and invalid CPU
state. These tests establish code behavior under the model, not physical CPU
power state or cache coherence.

This batch temporarily offlines CPUs and attempts to restore them. A new kernel
can hang during that operation, so its device result and recovery reentry remain
unverified until the manual test. It leaves Linux caches and MMU enabled, does
not stop DMA devices, does not change GIC ownership and never branches to XNU.
It cannot certify an executable XNU handoff.

Workflow inputs: `window_access=true`, `xnu_stage=true`, `cpu_cache=true`.
The local BOOT-only diagnostic ZIP explicitly identifies CPU state changes and
is paired with the original BOOT rollback. Builders only produce artifacts;
staging helpers only copy RAM files. Installation and reboot remain manual.
