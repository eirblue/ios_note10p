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

Source `65ed7864c15bf168cf9dbfb540fd0080d402579e` passed the full kernel
build in CI [40436768400](https://github.com/eirblue/ios_note10p/actions/runs/40436768400).
The local regression suite passed 168 tests, and 27 actual-UFS-C cases plus
the generated unlocked-DMA-hook executable passed. Actual Image/config/model
bindings, PID1, packaged BOOT and native updater syntax checks passed.
The first physical cycle passed on 2026-10-27, starting at 25% battery under
the explicitly user-authorized 10% minimum. Each phase had eight intact matching
records, with capture generation 1 and completed generation 2. Request, task and
LRB masks were zero throughout. The suspended sample reported IRQ disabled,
system suspended, power-down, link off, clocks off and gating suspended. The
restored sample reported IRQ enabled, system flag clear, active power/link and
clocks on. Existing PM, eight-CPU timer/GIC, DMA framework, RAM and payload checks
passed in the same cycle. A fresh TWRP boot ID and all five partition hashes
were verified after automatic return. No hardware register was read by the UFS
observer; independent hardware DMA-idle and XNU execution remain unverified.

The host-only battery policy update passed 169 regression tests. It changes
neither this compiled kernel nor its model/source bindings.

## Held-clock HCI extension (version 2, physical test pending)

`N10UFS2` retains the three driver snapshots and adds a single hardware read
sample from the pinned `ufshcd_suspend` callback, after host IRQ disable and
before reset-low or clock-disable calls. The original callback already holds
clocks and suspends gating. No new clock hold, PM request, IRQ operation or
controller write is introduced. The observer requires powered/mapped HCI,
CLKS_ON, gating suspended, PM in progress, IRQ disabled, power-down/link-off and
empty software masks before issuing three bounded reads under the host lock.
It reads controller enable and transfer/task doorbells; the strict decoder
requires controller disabled and both doorbells empty. Any unsupported state,
missing or duplicate callback, wrong owner/generation or nonzero value fails.
No read occurs from the later clock-off driver snapshot.

Arming is bound to the controller and capture generation. Phase 1 consumes and
disarms it, including lookup/lock failures; phase 2 cancels any leftover observer
after failed suspend. The native model checks read eligibility, both lock and
IRQ restoration, unchanged device state, and complete disarming in 42 cases.
The exact pinned callback preparation hash and its hold/IRQ/reset/clock order
are checked separately. All 170 host regression tests passed locally.

These observations describe one callback boundary; they do not establish
persistent DMA shutdown, other DMA engines or safe XNU/GIC/MMU ownership.
The version 1 physical result above remains historical evidence only. The
version 2 kernel must complete its own build and fresh single physical test.
