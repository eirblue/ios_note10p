# Guarded CPU0 CPU_PM notifier pair


The v50 source bundle corrects the v49 helper admission predicate: Linux `preemptible()` requires IRQs enabled, while the helper is intentionally called with local IRQs disabled. The caller retains its IRQ-enabled PC0 checks before saving IRQ state; the helper retains the owned-generation, CPU0-only, IRQ-disabled PC0 contract. The native provider uses the pinned Linux IRQ predicate rather than checking the preemption count alone. The v50 CI build and one physical cycle completed; the diagnostic result failed because the collector compared the pair's transaction generation with the later completed quiescence generation. Recovery and partition integrity passed.

A separate, versioned `N10CPT1` failure diagnostic preserves already stored terminal state when the enclosing sample reader fails. It records whether the helper was invoked, its stored attempt flag, the stage and outer error, and the saved enter/exit counts and return codes. Publication is bound to a completed current generation. Reporting adds no hardware reads, callback/API invocation, retry or cleanup call.

`N10CPR1` and its strict success predicate remain unchanged. Failure diagnostics are parsed independently and cannot mark a required pair evaluation passed. A failed or absent terminal record remains insufficient to establish a successful pair. The v50 result remains failed and its journal is never replayed. Any v51 physical confirmation requires a new artifact, plan and gates.

The experimental v49 `--cpu-pm-roundtrip` option is off by default. It requires the current EHLD running-lock audit and automatic recovery. Its marker is `CONFIG_NOTE10_CPU_PM_ROUNDTRIP`; its proof version is 1. A compiled option and successful input observations do not establish that a device has executed the pair.

The experiment uses the existing owned `TEST_PLATFORM` path after nonboot CPUs have been disabled. It keeps the original CPU-freeze cleanup. The worker must start and finish on CPU0 with only CPU0 online, IRQs enabled and preemption count zero. An outer local IRQ save covers admission and the pair. The notifier registration lock is used only for inspection; it is released before either CPU_PM API call, while local IRQs remain disabled and preemption count returns to zero.

A new guard in the CPU_PM translation unit can inspect its static notifier chain directly. Admission requires the exact six supported callback identities, order and priorities, the current PM generation and ownership, and supported input states. Unknown, missing, duplicate or changed callbacks, a busy inspection lock, context drift or repeated invocation prevent either call. The EHLD control lock must also be available to a single trylock attempt, and its running state must be valid before entry. Existing read-only collectors are not invoked twice to obtain this guard. This initial scope requires schedutil to be **not started**, avoiding timer and trace work from an incomplete PREPARE/POST sequence. Its timer linkage is not read when it has not been initialized for use.

Only after admission does the worker call the original `cpu_pm_enter()` once. On success it immediately calls the original `cpu_pm_exit()` once. An entry failure uses the kernel's existing successful-prefix rollback and does not receive an extra exit. An exit error is recorded without retry. IRQ and CPU re-online cleanup remain mandatory. No cluster CPU_PM, syscore, platform sleep, forced callback failure, panic, NMI or lock-contention injection is part of this experiment.

These APIs invoke real driver behavior: GIC register restoration, PMU stop/reset/restart, timer control restoration, FPSIMD save or lazy-state changes, and EHLD running-state changes. Fresh pre/post samples must verify full DAIF restoration, supported GIC controls, CNTKCTL and EHLD running state, together with CPU/mask/generation and preemption context. Historical samples provide baseline context; restoration checks use the new call window. Perf counts and lazy FPSIMD metadata are not required to remain bit-identical. New observers do not dereference performance-event objects. This is not a claim of complete hardware restoration, event lifetime safety, NMI safety or low-power readiness. The inspection and later API invocation are not a global atomic snapshot.

The new required row passes only for one actual successful API pair and every defined postcondition. Admission rejection must not be reported as a completed pair. API-call counts do not constitute a per-callback runtime trace. Existing inventory rows describe their earlier inspection phase; the new row records the later API pair. Existing evaluations remain: when enabled, the planned total is 43 rows with 42 required; when disabled, the existing 42 rows with 41 required remain.

Focused validation will bind the actual source transformation, extracted changed worker and cleanup paths, strict option/configuration/proof scope, and ON/OFF production package/precheck/collector behavior. Passed unchanged evidence is reused; previous validators and histories are not replayed locally. A successful actual 26-binding CI pipeline and a fresh reviewed plan are required before device execution. Device testing retains the immediate 10–100% battery gate, normal bound TWRP, five-partition integrity, one fresh cycle, automatic return and verified raw brightness 10 after pre/post integrity checks. The v49 implementation and actual CI build passed; its physical diagnostic did not establish a pair observation. The v50 evidence and preserved failed result are described below.


## v50 physical result and v51 generation binding

The single v50 diagnostic did not pass. Forty-one of 42 required evidence rows passed; the CPU_PM enter/exit pair row remained failed because the collector rejected the raw pair frames on a generation-binding mismatch. The saved frames are checksummed and carry the producer's transaction generation. The producer's terminal-read contract binds that transaction to the predecessor of the completed quiescence generation, while the v50 collector passed the completed value directly to the strict decoder.

The v51 correction is limited to the collector: validate the completed generation as a non-boolean uint32, convert it to its modular predecessor, and use that expected transaction generation for both success and terminal-failure decoding. The producer and strict decoders remain unchanged. Focused offline cases cover success, terminal failure, wraparound, malformed completed values, stale generations, identity mismatch and checksum mismatch. The saved v50 log decodes under the corrected binding offline; this does not revise the preserved v50 failed result.

## v51 verification and result

The v51 source commit was `bbf3b4bd8167cbbe103266d2da6809de4a9f8d3b`. CI run 40979304539 passed. The actual artifact review confirmed 26 binding validators and the new 10-case collector proof. The prior native 22-case, transform 6-case, native terminal 10-case and decoder 16/24-case proof bytes were reused; historical models were not rerun locally.

One fresh plan and one new journal cycle were used. The diagnostic passed all 42 required evaluations, including the strict CPU_PM pair generation check. The device returned automatically to the same normal TWRP environment; all five partition hashes matched, brightness raw value 10 was verified after integrity checks, and installation battery was 39%. The saved result records `single physical diagnostic passed` and binds to source commit `bbf3b4bd8167cbbe103266d2da6809de4a9f8d3b`; the result artifact is evidence for that source, not a separate source commit. Its SHA-256 is `20ea4047b6bf773143043ebb45049241c189e179948dd1c6651ae9ae2bed2c52`.

The v50 failed result and journal remain unchanged and were not replayed. This v51 result does not establish per-callback runtime tracing, complete hardware DMA shutdown, XNU execution or iOS boot.

## v52 aggregate notifier-count observation

The separate `--cpu-pm-notifier-counts` option is off by default and requires the existing guarded roundtrip option. It records aggregate callback-return counts from the same original `cpu_pm_enter()` and `cpu_pm_exit()` calls. CPU0-owned observation windows use bounded scalar RAM state; ordinary EXIT retains its NULL counter, and ENTER failure-prefix cleanup, notifier order/STOP behavior, return conversion and RCU flow are preserved. No additional CPU_PM, cluster, syscore, platform-sleep or driver calls are introduced.

The new two-copy, checksummed `N10CPN1` companion binds the raw transaction generation, identity, admitted roster and pair or terminal state. The existing CPR/CPT schema and strict pair verdict remain unchanged. When the option is enabled, the new required `cpu0_cpu_pm_notifier_counts` row passes only alongside a successful strict pair with six returned ENTER callbacks and six returned explicit EXIT callbacks. Missing, partial or inconsistent companion evidence fails the new row without promoting or reversing the independent pair verdict. The enabled plan has 44 evaluation rows, 43 required; existing packages without the feature retain 43 rows, 42 required.

Focused host evidence covers the actual transformed notify/enter/exit/helper paths, failure-prefix preservation, partial STOP traversal, reentry and foreign-CPU isolation, frame limits, strict parser binding and feature scopes. Package-flow fixtures call the production prepare/build/verify/stage/precheck/collect functions, but replace the CPU_PM binding validator with a scope-only stub and remain synthetic. Full artifact source/configuration/Image/proof binding and fresh one-cycle hardware confirmation remain required. Aggregate counts do not identify each callback or establish its runtime order, complete DMA shutdown, XNU execution or iOS boot.

## v52 verification and result

Source commit `0d7bf9ed8f1d7d51587123b8c8d9bb9817999dc6` passed [CI run 40996078899](https://github.com/eirblue/ios_note10p/actions/runs/40996078899). Review of the exact artifact confirmed 26 binding validators and the enabled notifier-count feature. Compile-only helper artifacts are selected by the presence of exactly one supported non-symlink filename, independently of the validator host; executable, source, compile-log and proof hashes remain required. Earlier failed CI attempts remain historical failures.

One fresh plan and one new physical journal cycle passed all 43 required evaluations out of 44 total rows. The strict CPU_PM pair and its valid companion passed together, with aggregate returns of six ENTER callbacks and six explicit EXIT callbacks. Automatic return to normal TWRP, matching hashes for all five partitions and brightness raw value 10 after integrity checks were confirmed.

The v49 and v50 failed results and the v51 successful result remain preserved; previous journals were not replayed. The v52 counts are aggregate traversal/return evidence. They do not establish each callback's runtime identity or order, complete hardware DMA shutdown, XNU execution or iOS boot.

## v53 dispatch-boundary observation

The `--cpu-pm-notifier-trace` option is off by default. `CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE` depends on both notifier counts and the guarded CPU_PM roundtrip. A separate source transformation layers the feature over the validated v52 prepared source; the previous CPR/CPT/CPN producers, verdicts and historical results retain their original contracts.

The observer surrounds the original `nb->notifier_call(nb, val, v)` statement in the generic notifier implementation. That statement, its operand, traversal, next-pointer read, return assignment, RCU scope, callback counter and STOP handling stay intact. Private non-exported helpers are armed only around the exact existing owned CPU0 ENTER or explicit EXIT notification. Every helper checks CPU0 before reading or writing shared observer state; the exact head address and event are then checked before callback payload access. A foreign finish returns a zeroed caller result without accessing the owner latch. Unarmed, unrelated-head, unrelated-event and foreign-CPU dispatches produce no observations. Matching nested dispatch invalidates the trace without changing notifier behavior.

Admission snapshots six notifier-block identities and their callback-field values under the existing registration lock. At dispatch, bounded RAM-only observers compare the block and a separate callback-field read with that roster. Six fixed scalar slots per phase encode entry and return order; transient head, block and callback pointers are wiped at helper completion and never serialized. There are no new driver calls, locks, allocation, logging or hardware reads in the observer, and the original single enter/exit pair and failure-prefix cleanup remain unchanged.

The two-copy, checksummed `N10CPD1` companion binds identity and transaction generation to successful strict CPR and CPN evidence. The independent required `cpu0_cpu_pm_dispatch_trace` row requires all six distinct admitted blocks to enter and return in order in both phases. Missing, unknown, duplicate, partial, reordered, recursive or conflicting evidence cannot pass that row; the existing pair and count verdicts remain independent. TRACE ON has 45 total rows and 44 required; TRACE OFF with COUNTS ON retains 44/43, and both features OFF with the roundtrip ON retains 43/42.

The accepted v53 CI artifact binds 22 focused native cases, 24 strict parser cases and 22 production package/binding cases. Synthetic fixtures retain explicit scope-only validator stubs. Exact artifact review confirmed configuration, source/Image/proof binding and private helper linkage before the fresh plan and existing safety gates authorized the single physical cycle reported below.

This observation establishes notifier-block identity/order at the generic dispatch boundary and equality of a separately read callback field to its admitted snapshot. It does not prove that this separate read was the exact indirect-call target loaded by the instruction, complete hardware DMA shutdown, XNU execution or iOS boot.

## v53 verification and result

Source commit `9c8410fac2fcca8cd7aeddb1ef79f5582c0a626f` passed [CI run 41010158045](https://github.com/eirblue/ios_note10p/actions/runs/41010158045). The production validation manifest records 26 unique binding validators, the existing 36 direct calls and 127 observed calls including nested invocations. Each completed invocation binds its module source and actual proof files; the manifest is bound to the build report and exact CI identity. Operator and independent parent reviews accepted the actual artifact without replaying historical validators locally.

One fresh physical cycle passed all 44 required evaluations out of 45 total rows. It used the same original single `cpu_pm_enter()` / explicit `cpu_pm_exit()` pair. Strict pair, count and dispatch companions passed together: both ENTER and EXIT recorded the six admitted notifier blocks entering and returning in roster order 1, 2, 3, 4, 5, 6, with aggregate counts of six plus six. These records establish block identity/order at the dispatch boundary and equality of a separately read callback field to its admitted snapshot; they do not establish the instruction-level indirect-call target.

The device returned automatically to normal TWRP. All five partition hashes matched, brightness raw value 10 was verified after integrity checks, and installation battery was 23%. An earlier preinstall stop at battery 0% remains preserved; no installation or reboot occurred during that stop. After battery recovery, only the single fresh physical cycle was executed. Previous journals were not replayed. The successful result artifact SHA-256 is `8fbeff09a4cf9266652d4a600563a968a0d4d64aaf1f87d39512e059aa5dcf17` and binds to the source commit above.

Earlier v53 [CI 41002376625](https://github.com/eirblue/ios_note10p/actions/runs/41002376625), [CI 41005053470](https://github.com/eirblue/ios_note10p/actions/runs/41005053470) and [CI 41008544786](https://github.com/eirblue/ios_note10p/actions/runs/41008544786) remain failed build records. Their host test input/workspace failures were corrected before the accepted build; they are not physical successes. The v49 and v50 failed results and all prior result history remain preserved. The v53 observation does not establish complete hardware DMA shutdown, XNU execution or iOS boot.


## v56 compatible observation passed

Tested CI source `e4e662059413fc1157df0587e4b088f762b0621f` passed
[CI 41075142026](https://github.com/eirblue/ios_note10p/actions/runs/41075142026),
attempt 1. Its actual manifest records 27 unique validators and 128 calls; the new
focused proofs contain native8/parser24/preparer18/package22 cases. The tested
source identity is separate from publication of this result documentation.

One fresh physical cycle passed all 45 required evaluations out of 46 total.
All 44 prior required keys remain independently required, including the original
CPU_PM pair, counts and dispatch trace. Normal automatic TWRP return, all five
partition hashes and brightness raw10 after integrity checks were verified.

The added `xnu_runtime_plan` row has two agreeing checksummed `N10XPO1` copies
bound to the same boot/build and current reservation. Its own generation is 1,
phase is late-init, and `pm_completion_claimed=0`. The observed facts retain
`synthetic=1`, `materialized=0` and `ownership=0`. They establish a hypothetical
local plan using a synthetic ADT; no new RAM layout or metadata was installed.
The old kernel-at-base writer and the earlier callback-identity/order limits
remain unchanged. This does not establish XNU execution, iOS boot, global DMA
quiescence or physical ownership. See [result and scope](XNU-RUNTIME-OBSERVATION.md).
