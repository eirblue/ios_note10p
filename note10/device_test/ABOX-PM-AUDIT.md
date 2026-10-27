# Read-only ABOX driver and normal callback observations

The next bundled build keeps the tested firmware guard and adds a separate
[bounded PMU control/standby observation](ABOX-PMU-AUDIT.md) to all previous
evaluations. The software observer here remains distinct from that PMU API
read lane, and neither establishes DSP/global DMA shutdown or XNU execution.

The pinned public DT identifies the remaining runtime/syscore IOMMU as ABOX
audio and explicitly marks it `sysmmu,no-suspend`. Its normal system suspend
callback does nothing; the notifier and runtime paths manage driver power.
The default-off `NOTE10_ABOX_PM_AUDIT` observation requires the existing IOMMU
and full UFS/HCI/PM diagnostic chain and built-in ABOX. All compatible prior
diagnostics remain in the same build and boot.

Three snapshots are bound to the existing PM owner/generation and taken after
the PM-list mutex is released. The observer references the compatible platform
device, takes its nonblocking device lock, validates bound driver and drvdata,
and copies software fields. IPC head/tail are copied under the existing queue
spinlock. Firmware state/version, enabled/restored flags, audio mode/CPU gear,
registered interface/channel counts, runtime status/error, usage/child counts,
disable depth and system PM flags are recorded. Negative usage is retained as
a signed-magnitude ownership observation; no count or status is overwritten.
These sequential reads are not a globally atomic driver/hardware snapshot.

Memory-only hooks record the original enable return and normal disable/IPC
results. The IPC call still happens exactly once under its original condition,
and its return remains ignored by the original disable path. Observation does
not call enable/disable/IPC, request PM, touch registers, read firmware payloads
or power down the DSP. Event history belongs to this boot/device and may predate
the diagnostic generation; the three snapshots show whether counts changed.
History and queue locks are not nested, and all references/IRQ flags are restored.

`N10ABX1` emits eight checksummed copies per phase. Two matching copies from all
three phases and the exact begin-to-completed generation advance (including
zero-skip wrap) are mandatory. Source pins, actual Image/config scope, generated
callback preparation and native harness hashes are checked before packaging
and installation. The actual observer/producer and generated event blocks pass
25 native cases, including unchanged return values with errors, default-off
blocks, missing/foreign devices, queue/field faults, locks/references/IRQs,
negative usage, active firmware and failed IPC. The generated DMA hook executes
only after releasing the PM list mutex.

A valid busy or failed-IPC observation is not an idle-state pass. The optional
`abox_driver_idle_state_observed` flag requires conservative software-idle
predicates; even that flag is not independent DSP/DMA shutdown proof. Registered
DMA channel counts do not establish active hardware transfers. DSP WFI/reset,
secure-world ownership, global DMA shutdown and XNU execution remain unverified.
Real driver state and callback history stay in private captures. The full
[integrated kernel build](https://github.com/eirblue/ios_note10p/actions/runs/40452870987)
passed at source `2baa761`. Its actual Image/config, bound native models and
initial process passed local verification, and a fresh single-cycle package was
prepared offline. The user then explicitly requested proceeding with this test
despite the reported battery below 10%. A private authorization bound to this
exact plan permitted one cycle with a 7% floor; the public 10% default remains
unchanged, and the exception does not apply to subsequent builds.

The fresh physical cycle passed all 13 evaluation items, returned automatically
to a new TWRP boot and passed all five partition checks. All three ABOX phases
were observed, but the conservative software-idle predicate was false. Runtime
ownership and queued work remained visible; valid observation is not an idle
or shutdown result. Detailed driver state and callback history remain private.

The complete local regression suite passed 194 tests. The combined generated
PM hook also passed the 25-case IOMMU and 42-case UFS/HCI actual-C models.

## Next build: worker and queue observations (evidence v2)

`N10ABX2` adds normal IPC worker starts/completions, its last observed stage and
in-flight flag, the signed-magnitude result of its original runtime get, and
the original firmware gate result. Successful queue puts/gets, full/empty
returns and the memory-only work-pending bit supplement the existing queue
indices. History belongs to this boot/device; it does not identify every
runtime reference owner or establish a causal relationship between sequential
snapshots. Queue events run after releasing the original queue lock, and the
history lock is never nested with it. Counts may wrap; no reference balance is
inferred from those counts.

The original runtime get, firmware gate and runtime put still execute once in
the same order. Their return/branch semantics are preserved, including the
original ignored runtime-get result. No extra get/put, flush, IPC request,
firmware read or power operation is introduced. Default-off builds retain the
original paths. The 36-case actual-C model exercises the observer/producer and
exact generated event blocks, including positive/negative runtime returns,
false/true gates, incomplete/completed work, pending work and full/empty queues;
it does not execute the full hardware worker. The local regression suite passed
201 tests. Existing UFS/HCI, IOMMU and other diagnostics remain bundled.

The CPU gear value alone is no longer part of the software-idle predicate: the
original driver's idle decision uses a separate QoS ownership query, not a zero
gear comparison. Completed historical worker/queue counts also do not prevent
current software idle. Active work, pending work or a negative last runtime-get
result prevent that optional flag. This correction does not alter the previous
physical result: its runtime ownership and nonempty queue independently failed
the idle predicates. Evidence v1 is not accepted as v2. The full
[v2 integrated build](https://github.com/eirblue/ios_note10p/actions/runs/40456766748)
passed at source `af14c01`; its actual Image/config, bound native models and
initial process passed local verification, and a fresh single-cycle package was
prepared offline. ABOX 36, IOMMU 25 and UFS/HCI 42 actual-C cases passed in the
downloaded CI artifact. Its fresh physical cycle later passed all 13 evaluation
items at 22% battery, with automatic TWRP return and all five partition checks.
The IPC worker completed its original runtime get and put, but its firmware
gate refused queue processing and work remained queued. The worker was not
still in flight at the snapshots; this does not identify every remaining
runtime reference owner or prove a DSP/DMA shutdown. Detailed records remain
private. The earlier one-cycle low-battery exception was not needed for this
cycle, and the 10% default minimum remains unchanged.

## Next build: firmware return and PM preparation (evidence v3)

`N10ABX3` retains the worker/queue observations, and a separate `N10ABR1`
companion records the original firmware-download result before the driver's
existing `-EAGAIN` to zero normalization. It also observes the normal ABOX PM
prepare notifier's entry, completion of its existing barriers/flush, original
clearable predicate, optional original runtime-suspend return and original
`NOTIFY_BAD`/`NOTIFY_DONE` outcome. No notifier, firmware request, PM operation,
QoS query or flush is added by the observer. Original calls and conditions
remain in the same order and execute once when originally applicable.

The main and companion frames require matching current generation and phase,
at least two intact identical copies per phase and exact source/model/Image
bindings. The companion has four copies per phase; main frames retain eight.
Separating them keeps each frame within the kernel line limit. Report samples
use a static cache on the existing single owned reporting lane to limit stack
use. Per-boot history is not per-generation ownership proof; absent callbacks
remain a valid observation, and a valid busy/error observation does not prove
idle. Old v1/v2 frames cannot satisfy v3.

The actual observer/producer and exact generated blocks pass 46 native cases,
including default-off behavior, unchanged normalized and nonnormalized firmware
returns, both clearable decisions, conditional suspend calls, preserved bad/done
returns, missing companion evidence and signed minimum return magnitude. These
models do not execute the full hardware firmware loader or PM notifier. The
full [v3 integrated build](https://github.com/eirblue/ios_note10p/actions/runs/40510283132)
passed at source `b4fd5e0`. The local regression suite passed 207 tests; the
downloaded CI artifact passed 46 ABOX, 25 IOMMU and 42 UFS/HCI actual-C cases.
Its actual Image/config, source/model bindings and initial process passed local
verification, and a fresh single-cycle package was prepared offline. Its later
fresh physical cycle passed all 13 evaluation items at 60% battery, returned
automatically to a new TWRP boot and passed the five partition checks. Firmware
download deferred with the original `-EAGAIN` result, while the normal prepare
notifier completed its clearable path and original runtime-suspend request
without a negative result. Later snapshots still retained runtime ownership and
a nonempty queue. This does not establish every owner's identity or DSP/DMA
shutdown; detailed firmware, callback and device records stay private.

## Next build: AUD QoS and normal runtime reference observations (v4)

The pinned QoS apply path takes a normal runtime reference on the AUD target's
zero-to-positive transition and releases one on the positive-to-zero transition.
`N10ABX4` retains prior diagnostics; the required `N10ABQ1` companion adds a
bounded read-only AUD request view and the original normal get/put outcomes.
The observer validates the exact QoS device and copies all 64 request IDs/values
and the original target under the existing QoS spinlock. After restoring IRQ
flags it validates contiguity, duplicate IDs and the copied maximum against
that target. It records registered/active
counts, target/applied values, default/absolute request values, only the first
active identity/value, and the work-pending bit. The first identity is not a
complete active-owner inventory. Names, firmware contents and MMIO are not read.
Applied value updates are not synchronized by the request lock, so this view
and its separate event history are not globally atomic.

Normal QoS worker entry/exit and conditional runtime get/put calls are observed
without changing original conditions, order, return handling or PM/QoS state.
There are no added PM requests, QoS updates, flushes or counter rewrites.
Observer history is copied separately from the request and IPC queue locks.
Counts may wrap and are not proof of runtime reference balance or ownership.
Active/pending QoS work, nonzero target/applied values or negative observed
runtime outcomes prevent the optional software-idle flag, without constituting
hardware shutdown proof.

Both previous companion evidence and four copies per phase of `N10ABQ1` are
required, with at least two matching copies per phase and exact generation,
source, helper, model, Image and config bindings. Old v3 evidence cannot satisfy
v4. PC regression passed 217 tests. The 66-case native model runs the actual
observer/producer, pinned target helper, original QoS apply and worker bodies
under controlled stubs, plus exact generated event blocks and default-off
paths. It checks active/queued releases and acquisitions, full/invalid arrays,
foreign devices, failures, counter wrap, missing evidence, unchanged targets,
non-AUD requests and work in flight. Model semantic assertions are separate
from decoder rejection so an unexpected result cannot pass as a rejection.
This is not full hardware QoS/PM execution. The full
[v4 integrated build](https://github.com/eirblue/ios_note10p/actions/runs/40516819807)
passed at source `02e4f5f`. The downloaded artifact passed 66 ABOX, 25 IOMMU and
42 UFS/HCI native cases, including the actual QoS backend, apply and worker
paths and default-off blocks. Its actual Image/config, source/model bindings
and initial process passed local verification; a fresh single-cycle package
was prepared offline. There is no v4 device staging, installation, reboot or
controller journal. Fresh v4 physical observations remain pending.


## v21 physical result and v22 lifecycle observation

The v21 single physical cycle passed all 13 bundled evaluations, automatic
TWRP return and five partition integrity checks at the normal battery floor.
AUD request target/applied values and pending/inflight work were zero at the
suspend observation. ABOX still had a runtime reference and queued IPC, so the
queued QoS-release hypothesis was not established and no barrier-order change
was made. QoS get/put event counts cannot establish full reference ownership;
the observed asynchronous get return also cannot independently prove a leak.

The next build uses `N10ABX5` plus mandatory `N10ABL1` lifecycle companions.
It observes the existing probe-time runtime get and the existing late-init
conditional put: count, original signed result, and signed usage samples
immediately before/after each original call. The original late init reports
whether data was missing, the platform device was missing, or the valid-device
branch ran. This state survives a later deferred probe without requiring a
valid device at late init. No extra runtime request, firmware, MMIO, flush,
reference decrement or power transition is introduced. Default-off paths keep
the original calls and conditions.

Late init preceding deferred probe is a hypothesis to evaluate on the device.
Usage samples and event history are not globally atomic; counts can wrap and
are not complete reference balance or ownership proof. The complete generated
late-init function, exact probe block, actual observer/producer, QoS bodies,
strict companion decoder and default-off paths are exercised by 79 native
cases. Existing 13 evaluation items remain bundled. v22 physical observations
and DSP/global DMA shutdown or XNU execution remain unverified.


The [v22 integrated kernel build](https://github.com/eirblue/ios_note10p/actions/runs/40522790002)
passed at source `8fbe4a2`. Local regression passed 220 tests. The downloaded
artifact passed source/Image/config and native model bindings for 79 ABOX,
25 IOMMU and 42 UFS/HCI cases. The initial process and a fresh one-cycle private
plan/package passed offline validation. No v22 staging, installation, reboot
or controller journal was created. This completes the requested v21 physical
cycle plus next compilation; v22 physical lifecycle observations remain pending.


The v22 single physical cycle passed all 13 evaluations, automatic TWRP return
and five partition integrity checks. The original probe get and late-init put
both ran and returned success, with the sampled usage respectively increasing
and decreasing normally. The valid-device late branch ran; a skipped late init
was not established. A runtime reference and queued IPC remained later, while
AUD target/applied/pending/inflight values were zero. Further ownership tracing
is required. These observations do not prove globally atomic reference balance,
DSP/global DMA shutdown or XNU execution. Raw captures and identifiers remain
private. Direct result-driven test/build continuation is now user-authorized.


## v23: observe the system PM core's original reference pair (evidence v6)

The v22 private three-phase software samples show usage 0 before device PM,
1 while system-prepared/suspended, and 0 after completion. The pinned
`drivers/base/power/main.c` takes `pm_runtime_get_noresume()` in
`device_prepare()` to prevent runtime suspend through the system transition,
and calls the existing `pm_runtime_put()` in `device_complete()` or the
prepare-error rollback. This is a concrete alternative to a leaked driver
reference; v22 did not observe these calls, so attribution remains unverified.

v23 keeps every previous diagnostic and companion, changes the main marker to
`N10ABX6`, and requires `N10ABD1` with the signed before/after samples and original
results for these three core call sites. The noresume API returns void; its
result slot is a fixed zero, not a reported API success result. Core events are
filtered to the bound ABOX driver before touching its memory-only history.
No get/put, callback, barrier, flush, counter rewrite or MMIO operation is added.
Original conditions, order and ignored put results are preserved. Exact pinned
core input/output, generated blocks, observer/producer, Image/config and native
model hashes are bound together; v5 evidence cannot satisfy v6.

The 87-case actual-C model retains all prior 79 cases and adds the core call
blocks with successful/error releases, prepare-error rollback, counter wrap,
signed negative samples, foreign-device filtering and missing/invalid companion
rejection. It executes exact generated core blocks under controlled PM stubs,
not the entire hardware PM core. Default-off blocks preserve original calls.
The PC regression suite passes 222 cases. All five frame types fit the existing
896-byte payload buffer even at their unsigned field bounds. Physical v23
observations remain pending. Counts/samples are not globally atomic ownership
proof, and neither a balanced core pair nor diagnostic success establishes
DSP/global DMA shutdown or XNU execution.


The [v23 integrated build](https://github.com/eirblue/ios_note10p/actions/runs/40528298054)
passed at source `f258172`. Its first host preinstall check stopped before any
partition write or reboot because the embedded diagnostic package still said
v5 while its pair metadata said v6. Host fix `c1a2d6e` synchronizes the version
and verifies pair/record/embedded metadata offline before RAM staging. The real
package regression and full suite pass 223 tests. That stopped journal is
preserved; a fresh corrected package/token/plan/journal performed exactly one
physical cycle using the unchanged verified kernel/model sources.

The physical cycle passed all 13 evaluations at 82% battery, automatically
returned to a new TWRP boot and passed all five partition integrity checks.
The original PM core prepare get and complete put were both observed, adding
and releasing one reference normally. A pre-existing reference remained before
and after that pair. In this boot, unlike v22, AUD target was zero while applied
value and pending work remained nonzero, and an original QoS release had not
yet been observed. These timing-dependent samples warrant bundled QoS/runtime
queue and event-order analysis. No leak is inferred from the asynchronous get
return; no reference is forcibly released. DSP/global DMA shutdown and XNU
execution remain unverified. Raw captures and identifiers stay private.


## v24 bundled async/runtime trace (evidence v7)

All 13 evaluations remain bundled. This build combines the preceding reference,
QoS, IPC, UFS/HCI and IOMMU observations with two required companions rather
than issuing a separate physical build for each new observation. `N10ABT1`
records runtime request type/pending, deferred resume, idle notification,
autosuspend use/timer flags and whether the expiry field is nonzero. These
fields are copied together under the existing runtime-PM spinlock, separately
from the QoS, IPC and event locks. A nonzero expiry field is not independent
proof that a timer is pending. The original runtime snapshot was taken
separately, so the combined snapshot remains sequential, not globally atomic.

The exact pinned firmware completion callback retains its original single
`pm_runtime_resume()` call, including when its firmware pointer is null. Only
pointer presence, signed original resume result and signed usage before/after
are recorded; firmware names, pointers and payloads are not emitted. Resume
itself does not inherently acquire a usage reference. Negative asynchronous
returns do not independently establish a reference leak. `N10ABO1` adds
completion-order stamps for enable, firmware download, PM prepare, QoS worker,
IPC worker, system reference pair and firmware completion resume. Stamps are
recorded after the original calls under the history lock, may wrap and cannot
prove exact start times, atomic ownership or absence of all other callers.

`N10ABX7` requires both new companions plus all previous companions, strict
phase/generation/checksum/copy validation and exact main/core/QoS source, model,
Image and config binding. No PM request, firmware request, flush, barrier,
counter rewrite or MMIO operation is added. The optional software-idle flag
also conservatively rejects pending runtime requests/deferred resume/idle
notification/timer-expiry state and negative observed async resume outcomes.
This does not establish DSP/global DMA shutdown or XNU execution.

The actual-C model passes 100 cases, retaining the preceding 87 and executing
the pinned full firmware completion callback under controlled stubs, locked
runtime field copies, present/null firmware, successful/positive/error and
in-progress returns, signed samples, foreign-device filtering, event-order wrap,
missing companions and invalid queue/sign rejection. Default-off paths retain
the original single callback call. Full PC regression passes 226 tests; all
seven frame types fit the existing payload buffer at unsigned bounds. Device
observations for this v24 build remain pending.


The [v24 integrated build](https://github.com/eirblue/ios_note10p/actions/runs/40534155951)
passed at source `1c565d0`; its actual Image/config, source bindings, 100 ABOX,
25 IOMMU and 42 UFS/HCI C models and initial process passed offline verification.
A fresh single physical cycle passed all 13 evaluations at 80% battery,
automatically returned to a new TWRP boot and passed five partition checks.

The firmware completion resume callback ran twice. The last firmware pointer
was absent, the last resume returned positive/already-active and did not
increase usage. Only the last presence was recorded, so both callbacks cannot
be labeled failed-firmware completions from this evidence alone. The normal
PM prepare entry preceded the later firmware-download/enable and last callback
completion records. QoS work drained in this boot; the system PM reference
pair was balanced, with no usage before/after and its normal protective hold
during prepare. Runtime remained active, with an autosuspend expiry before
prepare and a pending idle request after completion. This is not leak proof.
The pinned firmware loader sets its output pointer to NULL on failure and
still invokes the callback. A source-backed next candidate is a separately
opt-in failed-firmware callback guard, retaining successful/default-off behavior
and adding complete present/absent/skip counts in the same bundled evaluation.
No speculative barrier change, forced put, DSP/global DMA shutdown or XNU
execution is claimed. Raw evidence remains private.


## v25 bundled failed-firmware completion guard (evidence v8)

The separately default-off `NOTE10_ABOX_FW_FAILURE_GUARD` adds an early return
only when the original completion callback receives no firmware. Successful
callbacks retain exactly their original single runtime-resume call and ignored
return; with the guard disabled, null and non-null callbacks retain the original
behavior. The integrated diagnostic build explicitly enables and requires the
guard together with the existing full diagnostic chain. Actual config, build,
BOOT and pair/record/embedded package metadata are checked before installation.
No firmware request, forced runtime-reference release, PM counter rewrite,
barrier change, reset or MMIO access is added by this fix. Its physical effect
remains unverified until the new single-cycle result is collected.

`N10ABX8` keeps all prior bundled evaluations. Required `N10ABT2` extends the
trace with all-callback present/absent/skipped counts and the active guard bit;
`N10ABO1` adds the skip completion order. The last presence now refers to the
last callback, while the last resume fields refer to the last call that actually
resumed; they can belong to different callbacks when the guard skips one.
Counts/order stamps wrap and are not atomic reference ownership proof. Older
v7/trace-v1 evidence cannot satisfy v8. Complete present/absent counts avoid
mistaking the prior last-null observation for proof that both callbacks failed.

The actual-C model passes 105 cases, including the successful, null-skipped,
mixed callback sequence, wrapped skip counts, unchanged signed/positive/error
resume returns, foreign-device handling and every earlier diagnostic case.
Separate executables also exercise both guard-and-audit disabled behavior and
audit enabled with the guard disabled. Those paths preserve original null and
non-null resume calls. Full PC regression passes 227 tests and all seven
frame types fit the existing buffer. The next physical cycle retains all
13 evaluation items and adds the guard/count observations in that same boot.
DSP/global DMA shutdown and XNU execution remain unverified.


The [v25 integrated kernel](https://github.com/eirblue/ios_note10p/actions/runs/40538317465)
passed at source `42f042e`. Actual Image/config, guard metadata, 105 ABOX,
25 IOMMU and 42 UFS/HCI C models, initial process and fresh package all passed
offline verification. Its single physical cycle passed all 13 evaluations at
76% battery, automatically returned to a new TWRP boot and passed all five
partition integrity checks.

This boot recorded no present-firmware callbacks, two absent callbacks, two
guard skips and no callback runtime-resume calls. ABOX stayed runtime-suspended
in all three snapshots; usage was zero around the ordinary protective system
PM reference, QoS target/applied/pending values were zero, and the original
QoS get/put counts were balanced. The driver recorded one enable and one
disable, rather than the later re-enable seen previously. IOMMU runtime and
policy-active counts were also zero. The IPC queue remained nonempty and was
not discarded. These observations establish the tested software/runtime effect
of this opt-in guard, not complete DSP/global DMA shutdown or XNU execution.
A next bundled hardware observation will require bounded, source-validated PMU
reads with control-bit and standby semantics stated separately from electrical
power-off acknowledgment. Raw logs and identifiers remain private.
