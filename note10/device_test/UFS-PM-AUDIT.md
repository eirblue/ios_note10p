# Read-only Exynos UFS PM driver-state observations

The default-off `ufs_pm_audit=true` input requires the restored DMA/PM/GIC
diagnostic and automatic recovery. Four UFS source/header files are pinned.
An observer is included in the built-in Exynos driver. It finds the compatible
platform device, holds its reference, takes a nonblocking device lock, verifies
the bound driver and HBA association, then copies queue/link/clock/IRQ fields
under the existing SCSI host lock with IRQ flags restored. All references and
locks are released on every path. A missing controller or failed trylock remains
a failed observation. No PM request, host/device field or MMIO register is written.

The actual generated DMA observer calls it only after releasing the PM device
list mutex. It captures before device preparation, after successful asynchronous
suspend completion, and after resume/complete. The existing owner and generation
guard scopes these calls. No device lock is acquired under the PM list mutex.
Normal PM callbacks, TEST_DEVICES and low-level-entry blocking remain unchanged.

After PM/quiesce restoration, `N10UFS1` emits eight checksummed copies of each
phase. Sequence is `copy * 3 + phase`. Sequence, phase, generation, error and
status are decimal; other fields are hex. Records retain the begin generation,
and the reader/decoder require the exact USB completed-generation increment
including the zero-skip wrap. At least two intact matching records per phase
are required. Nonzero request/task/LRB masks, PM-in-progress, failed powered
state, missing records or inconsistent snapshots reject the diagnostic.

The suspended sample must report system suspend, disabled IRQ, clocks off,
gating suspended and a low-power device/link state. The pinned Exynos runtime
callbacks also call the system PM helpers; therefore a restored device may
either have a clear system flag or report runtime-suspended together with the
same idle driver predicates. This does not force a resume or rewrite a flag.

Actual Image/config scope and source/actual-C model hashes are checked before
packaging and installation. The native model executes the actual observer and
producer with lifetime, lock, IRQ and immutable-device checks. A second native
executable runs the actual generated DMA helper and verifies phase/generation
calls happen with its list mutex unlocked. Host binding recomputes that generated
helper hash from the exact recipe instead of trusting matching metadata alone.

These are software driver observations, not independent hardware DMA-idle or
global DMA shutdown proof. Other DMA engines, secure-world ownership, GIC/MMU
handoff and XNU execution remain unverified. Every new build requires a fresh
single physical cycle; raw logs and packed BOOT images stay private.
