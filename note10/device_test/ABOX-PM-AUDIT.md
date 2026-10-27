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
prepared offline. Battery was below the user-authorized 10% minimum, so this
build has no device staging, installation, reboot or physical result. Its ABOX
observations and complete 13-item physical evaluation remain pending charging.

The complete local regression suite passed 194 tests. The combined generated
PM hook also passed the 25-case IOMMU and 42-case UFS/HCI actual-C models.
