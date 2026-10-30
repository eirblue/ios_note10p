# Planned late-init runtime-plan observation

v56 adds a default-off `--xnu-runtime-observation` flag and
`CONFIG_NOTE10_XNU_RUNTIME_OBSERVATION`. Focused checks, actual full kernel CI,
source/artifact acceptance and any separately gated device cycle are pending.
The last physical baseline remains v53 (44 required of 45 total); v54/v55 supply
accepted PC evidence. Enabled scope requires the complete existing
trace/count/pair, staged payload, PM and automatic-recovery chain and adds one
independent required row, for 45 required of 46 total. Disabled scope retains the
previous schema and behavior.

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

New focused native cases compile the production planner and companion in a host
harness. Adapter/decoder and synthetic package/precheck/collector fixtures isolate
the new feature while reusing earlier saved evidence. Old models are not replayed
locally. The actual full build records the new binding validator through the
existing execution recorder, including real completed calls and proof hashes;
expected validator names alone cannot satisfy that closure. Test workspaces remain
project-private and disjoint from input artifacts, with bounded file-map copies.
