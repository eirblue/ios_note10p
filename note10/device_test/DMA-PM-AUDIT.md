# DMA-capable device PM framework coverage

The default-off `dma_pm_audit=true` workflow input requires the restored GIC/PM
diagnostic and automatic recovery. It captures three bounded read-only snapshots
of the pinned PM core device lists: before `dpm_suspend_start`, after its
successful return (including asynchronous callbacks), and after `dpm_resume_end`.
Only the diagnostic owner and its USB/display quiesce generation can capture.
The original callbacks, TEST_DEVICES boundary and reverse restoration stay intact.

Each snapshot counts all listed devices (maximum 4096) and identifies DMA-capable
devices by DMA-mask pointer or nonzero coherent mask. For these it counts system
PM suspended, direct-complete, syscore and uncovered categories, prepared flags
and runtime states. Counts and commutative bounded device-name hashes let the
decoder detect inventory changes. These hashes are not collision-proof identity
or hardware evidence. No device lock is taken under the PM list mutex, and no
device state, PM callback or MMIO register is written. Runtime observations may
change independently and are not treated as hardware-idle proof.

All printing occurs after normal PM/quiesce restoration. `N10DMA1` records carry
the current build ID, quiesce generation, phase and checksum. Eight copies of
each phase are emitted. Sequence is `copy * 3 + phase`; sequence, phase,
generation, error and status are decimal, and other numeric fields are hex.
At least two intact matching records per phase, consistent inventory digests,
valid count sums and clear initial/restored prepared/suspended flags are required.
Uncovered devices are reported as observations rather than hidden or forcibly
suspended. Even a fully covered framework inventory does not establish hardware
DMA shutdown: PM core flags can be set without a hardware suspend callback.

The captured generation belongs to the USB quiesce begin transaction. Normal
USB restoration advances ownership once and skips zero on overflow. The kernel
reader and host decoder both require this exact begin-to-completed transition,
including `0xffffffff -> 1`, while all three snapshots must retain the same
begin generation. An unchanged, missing or unrelated completion is rejected.

Actual config/Image markers prevent metadata opt-out. Source and actual-C
backend/producer model hashes are checked before packaging and installation.
The native model checks no device/list mutation, bounded traversal, missing or
duplicate phases, changed generation/inventory, restored-flag faults and corrupt
count sums. A new-build physical cycle remains required. This audit grants no
DMA shutdown, GIC ownership, MMU/cache handoff or XNU execution claim.

The host checks the exact two-stage suspend-source composition: the existing
guarded PM patch model has its own pinned output hash, while the added DMA
observer recipe has a different final output hash. Both must match their fixed
recipes; comparing those two legitimate stages directly would reject the audit
before installation. The integration test executes both actual preparation
recipes against the pinned upstream source and rejects wrong base/final hashes.

The first physical cycle of source `50f4fed3722ebfb48303a6bafdae3c89fb7e36bf`
(CI [40428263519](https://github.com/eirblue/ios_note10p/actions/runs/40428263519))
returned automatically to TWRP and passed all five partition hashes, PM and GIC
checks. The DMA diagnostic failed closed: its original reader incorrectly
compared the saved begin generation with the advanced completion generation.
All three phase records had generation 1 but status 1; completion was generation
2. Their raw counts were 1388 total devices and 277 DMA-capable devices, with
276 suspended and one syscore device at the suspend boundary. These failed
records are observations, not a passed audit or hardware DMA-idle proof.
Host precheck/collection errors were repaired separately; the stopped journals
remain preserved. That kernel was booted once, and subsequent collection and
integrity completion were read-only. The corrected generation rule requires
a new kernel build and a new physical cycle.

The corrected source `8e7ea2f17b314138f30a0b9d1995217b0712fb7e`
(CI [40431280403](https://github.com/eirblue/ios_note10p/actions/runs/40431280403))
passed one new physical cycle on 2026-10-27 KST. All three phases had eight
intact matching records, begin generation 1 and successful completion generation
2. The inventory stayed at 1388 total / 277 DMA-capable devices with unchanged
name digests. The suspend boundary showed 276 system-suspended, one syscore,
zero direct-complete and zero uncovered devices; initial/restored prepared and
suspended counts were zero. PM/quiesce and all eight GIC CPU PMR checks passed.
The controller completed its journal normally, observed a fresh automatic TWRP
boot and verified all five partition hashes; post-collection read-only checks
also passed. Local regression tests passed 156 cases and the actual DMA C model
passed 15 cases. Runtime-active count at the suspend boundary was 10, so these
system-PM framework observations still do not establish hardware DMA idle.
UFS queue/link/clock observations and the remaining handoff work remain pending.
