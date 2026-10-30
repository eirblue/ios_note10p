# Verified late-init runtime-plan observation

v56 passed [CI 41075142026](https://github.com/eirblue/ios_note10p/actions/runs/41075142026),
attempt 1, for tested source `e4e662059413fc1157df0587e4b088f762b0621f`.
The actual execution manifest records 27 unique validators and 128 calls. The
new CI proofs passed native8/parser24/preparer18/package22 cases. This identifies
the tested CI source; publication of the result documentation is separate.

One physical cycle passed all 45 required evaluations out of 46 total. All 44
previous required keys were preserved and the independent `xnu_runtime_plan` row
passed. Normal automatic TWRP return, five matching partition hashes and
brightness raw10 after integrity verification were confirmed.

The actual selected-boot evidence contains two agreeing checksummed `N10XPO1`
copies bound to the same build ID, current reservation, staged payload and
validated geometry. They record `phase=late-init`, own `plan_generation=1`,
`pm_completion_claimed=0`, `synthetic=1`, `materialized=0` and `ownership=0`.
The planner's generation is independent of PM generations. The existing PM rows
provide their own completion evidence; this companion makes no PM completion
claim.

The feature remains default-off through `--xnu-runtime-observation` and
`CONFIG_NOTE10_XNU_RUNTIME_OBSERVATION`. Enabled scope requires the full existing
trace/count/pair, staged payload, PM and automatic-recovery chain and adds one
required row (45/46). Disabled scope retains the earlier 44/45 schema. Accepted
v54/v55 PC results and the v53 physical predecessor remain preserved.

A separate full-path source adapter preserves the original reservation preparer,
v55 canonical-only helper, reusable C, header and wrapper byte pins. It checks
original and final provider provenance, exact old stage/cache guards and composed
source hashes before adding guarded includes and a synchronous tail call.
Before and final source snapshots identify their actual bytes separately. The
original timer source and its accepted final composed provider have distinct
hashes; they are not interchangeable.

The call follows the original successful stage/cache guards, early recovery-arm
call and PM timer scheduling call while late-init `__init` text remains live.
Planner failure reports only and does not bypass armed recovery or return from
the old caller. Scheduling order is source provenance, not measured timer-worker
progress. The companion records `phase=late-init`, `plan_generation=1` and
`pm_completion_claimed=0`; independent old rows remain necessary for PM completion.

Two bounded checksummed companion copies bind the selected build ID, current
reservation extent, staged payload and canonical geometry digest to validated
local-plan facts. The decoder requires both copies to agree with the selected
boot's reservation evidence and external package/build closure. It rejects
missing, duplicate, conflicting, damaged or wrong-generation evidence. Image and
source hashes are verified externally rather than embedded self-referentially.

The computed metadata-prefix and relocated-kernel offsets are hypothetical and
**materialized=false**. They overlap bytes used by the unchanged old kernel-at-base
data-only writer. No new window access, metadata write, serializer, CPU_PM pair,
PM/MMIO/register API or transfer is added. No relocated image readback, live ADT,
physical ownership, GIC handoff, DMA quiescence, XNU execution, iOS boot or readiness
is claimed.

Focused native cases compile the production planner and companion in a host
harness; those synthetic proofs are separate from the actual physical companion.
Package/precheck/collector fixtures isolate the new feature while reusing saved
evidence. The actual full CI records the real production binding calls and proof
hashes; an expected validator list alone does not establish that closure.

Failed [CI 41066125298](https://github.com/eirblue/ios_note10p/actions/runs/41066125298)
and [CI 41067698092](https://github.com/eirblue/ios_note10p/actions/runs/41067698092),
and cancelled [CI 41072098813](https://github.com/eirblue/ios_note10p/actions/runs/41072098813),
remain part of the history. Source preparation/profile pin ordering, artifact
proof retention and synthetic fixture isolation/staging were corrected before
the accepted CI. These earlier runs are not physical successes.
