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
the idle predicates. Evidence v1 is not accepted as v2; the next build and its
new physical observations are still pending. The one-cycle low-battery exception
has been consumed; future physical cycles retain the 10% default minimum.
