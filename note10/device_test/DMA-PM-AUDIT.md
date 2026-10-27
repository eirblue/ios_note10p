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

Actual config/Image markers prevent metadata opt-out. Source and actual-C
backend/producer model hashes are checked before packaging and installation.
The native model checks no device/list mutation, bounded traversal, missing or
duplicate phases, changed generation/inventory, restored-flag faults and corrupt
count sums. A new-build physical cycle remains required. This audit grants no
DMA shutdown, GIC ownership, MMU/cache handoff or XNU execution claim.
