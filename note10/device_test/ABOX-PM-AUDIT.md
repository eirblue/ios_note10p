# Read-only ABOX driver and normal callback observations

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
