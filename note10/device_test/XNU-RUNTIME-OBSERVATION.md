# Verified late-init runtime metadata observations

## v57 caller-owned scratch result

Tested source `5afedf0bd305861b1b98e7b975ad9a6405d38b6a` passed
[CI 41109866784](https://github.com/eirblue/ios_note10p/actions/runs/41109866784),
attempt 1. The canonical manifest measures 28 unique production validators and
129 actual calls. Both required named API steps completed successfully; genuine
post-command receipts independently bind the pinned workflow/helper, runner
context, original dispatch inputs and selected output bytes to the verified
artifact ZIP digest.

One fresh physical cycle passed all 46 required evaluations out of 47 total.
The complete v56 set of 45 required keys was preserved; the added independent
`xnu_runtime_scratch` row passed. Changed recovery boot identity, fresh normal
bound TWRP and matching hashes for all five partitions established automatic
return and integrity. Brightness raw10 was verified after integrity checks;
installation battery was 29%. The saved result SHA-256 is
`0a169946fa423240ac2ea35ec4b152e790f83e72a0f607593928d8cc2578105b`.
This result publication is separate from the tested source commit.

The default-off `--xnu-runtime-scratch` option and
`CONFIG_NOTE10_XNU_RUNTIME_SCRATCH` require the existing runtime-observation and
full payload/PM/trace/recovery chain. A private caller-owned `__initdata` object
holds bounded buffers for 1152-byte boot_args, a 64-byte transfer record and a
56-byte synthetic leaf ADT. The production serializer/checker roundtrips every
expected byte and canary and clears the private scratch object after use.
Focused host proofs contain native11/parser29/adapter4 cases, plus 24 production
package-flow cases; those synthetic proofs are distinct from the real boot log.

Two agreeing checksummed `N10XSO1` copies bind the current boot/build,
reservation, payload and geometry. They report `phase=late-init`, their own
generation 1 and `pm_completion_claimed=0`, with `bytes_checked=1`,
`canaries_checked=1`, `synthetic_adt=1`, `scratch_materialized=1`,
`reserved_materialized=0`, `ownership=0` and `executed=0`. Existing `N10XPO1`
semantics and the independent PM evidence rows remain unchanged. The serializer
writes only the private scratch object; the old kernel-at-base writer is
unchanged. No new metadata or hypothetical runtime layout was installed in the
reserved RAM window, and no ownership or execution transfer occurred.

The retained compiler estimate is 7,840 bytes against a 16,384-byte task stack,
leaving an estimated 8,544-byte margin. Its 2,048-byte external allowance is an
assumption: the saved compiler inputs do not measure every initcall ancestor,
exception/IRQ return, preemption/scheduler or console path. The fixed-leaf proof
is tied to the same actual source/object and the planner/scratch paths are
sequential. This is not a measured whole-OS stack bound or a general physical
stack-safety proof; the single device observation does not remove that limit.

Failed [CI 41090887005](https://github.com/eirblue/ios_note10p/actions/runs/41090887005),
[CI 41097401475](https://github.com/eirblue/ios_note10p/actions/runs/41097401475) and
[CI 41101985523](https://github.com/eirblue/ios_note10p/actions/runs/41101985523)
remain failed. Compiler sidecar provenance/capture, fixed-leaf estimation and
the terminal validator schedule were corrected before the accepted run. Failed
artifacts, prior results and journals were preserved; no previous physical
journal was replayed. Neither this result nor the synthetic ADT establishes
live hardware ADT readiness, global DMA shutdown, physical ownership, XNU
execution or iOS boot.

## v56 preserved planner observation


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
