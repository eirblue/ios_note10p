# Bounded ABOX PMU control and standby observations

The v25 failed-firmware completion guard passed its single physical cycle:
two absent callbacks were skipped, ABOX stayed runtime-suspended through the
three software snapshots, and the normal system PM reference was balanced.
The new default-off `NOTE10_ABOX_PMU_AUDIT` adds a separate required observation
to the existing 13 evaluations in the same diagnostic boot. It preserves the
proven guard and every prior diagnostic.

The observer uses only the existing exported `exynos_pmu_read()` API for the
two public-DT core tuples. It reads power and enable **control** bits and the
existing standby masks in PMU_ALIVE. Control bits are not electrical power-off
acknowledgments. These sequential API values cannot prove complete DSP/global
DMA shutdown, secure-world ownership or XNU execution. There are no PMU writes,
updates, clocks, reset, firmware or runtime-PM requests in this observer.

Before any read it finds and references the compatible ABOX parent, takes its
nonblocking device lock, and validates its bound driver name. It examines at
most 64 available child nodes, requires exactly the two compatible core IDs,
checks every offset/mask against the pinned DT allowlist, and references and
nonblockingly locks both platform devices. Each core must be bound to the
exact pinned core driver and match its parent and node. All devices and tuples
must pass before the first of six reads. It avoids the mutable global core
list. Locks and node/device references unwind on every path; PM-list, QoS,
IPC and event locks are absent from this read lane.

The actual `CONFIG_EXYNOS_PMU=y` is mandatory. The vendor header's disabled
stub returns success without filling an output, so both configuration binding
and the C observer refuse that case before any lookup or read. A null/error
PMU regmap is also refused. A read error invalidates the observation and cannot
turn zero-initialized fields into successful power evidence. The source pins
cover the original PMU driver/header and public DT; the final core source is
bound as the exact preceding guard source plus the separately conditional
observer include. Existing callback models still execute that unchanged base
prefix, while the new model binds the final composition and helper.

`N10APM1` supplies four checksummed copies per core/phase, bound to the existing
owner/generation lane after the PM-list mutex has been released. Two matching
intact copies of both cores in all three phases are mandatory. The decoder
checks phase/core/sequence, generation advance including wrap, count, error,
status and every masked value. Scope cannot be removed through metadata when
the actual Image/config contains this feature. BOOT and pair/record/embedded
package flags/version are checked before staging and collection.

The new actual-C model passes 34 scenarios using the real observer/producer
and pinned PMU read/getter function bodies under controlled stubs. It covers
all six read failures, missing/foreign devices, locks/references, invalid or
duplicate IDs, bad offsets/masks/properties, unavailable regmap, excessive
children, reversed core order, generation/copy faults and the no-config stub
refusal. There are no write/PM/clock APIs available to the model. The generated
DMA call executes only after releasing the list mutex. The retained ABOX 105,
UFS/HCI 42 and IOMMU 25 actual-C cases pass with the combined hook, and full PC
regression passes 236 tests. The real package regression also verifies the new
PMU version in pair/record/ZIP metadata. Physical PMU observations are pending.
