# Timed read-only post-resume PMU observations

The v29 guarded late/noirq physical cycle passed all 18 evaluations. Its 16
domain configuration/status/configuration masks changed from 0x4000 before
suspend to 0x0000 at noirq and 0xffff immediately after resume. The original
FSYS0A predicate allowed one successful original power-off control call.

The pinned generic power-domain core powers domains on during resume_noirq,
then pm_genpd_complete() queues power-off work after its prepared count reaches
zero. An immediate all-on snapshot alone cannot establish a persistent leak.

v30 adds default-off CONFIG_NOTE10_PMU_SETTLE, dependent on the proven guarded
noirq profile. After successful PM/timer reporting it schedules read-only
samples at targets of 1, 5 and 15 seconds. Each sample reads the existing 16
PMU_ALIVE configuration/status/configuration tuples: 48 reads, 144 total.
There are no added power, clock, device PM, reset or firmware requests and no
workqueue flush. The observer cannot force the sampled domain state.

The PM mutex protects each bounded read lane. The prior owner must be released,
the PM test level restored, and the successful noirq transaction, regular
samples and restore counters must still match. The lane rejects missing,
out-of-order or duplicate samples, stale generations and every read failure.
Each timed N10PST1 lane requires two consistent checksummed copies, matching
generation and completion, correct target and measured elapsed time. Targets
are relative to the end of PM reporting, and valid execution is bounded to
30 seconds; they are not exact scheduling guarantees. Samples remain sequential.

The new C models cover 183 actual PMU/gate scenarios, including all 144 read
fault positions, and 12 actual delayed-worker scenarios covering early/late
execution, scheduling errors, failed reads, duplicate arming and jiffies wrap.
Missing real PMU configuration must fail without reads. Full regression is
262 tests. CI and the single v30 physical cycle are pending.

The new required evaluation is pmu_settle, alongside the prior 18. Acceptance
requires complete observation rather than any particular power-state bitmap.
These samples do not prove global DMA shutdown, secure-world quiescence,
hardware GIC/MMU/cache handoff or execution of XNU/iOS. Screen logging stays off.
