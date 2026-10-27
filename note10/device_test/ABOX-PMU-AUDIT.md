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
PMU version in pair/record/ZIP metadata.

## Single physical result

Source `08d944ccc584bb7b24819ded5b74e729645e0639`, CI `40545543987`,
passed one fresh physical diagnostic cycle with all 14 evaluations, automatic
TWRP return and five expected partition hashes. The preinstall battery was 73%.
Both cores supplied all four intact copies in every phase without read errors.
In phases 0/1/2, both power and enable control bits were zero; masked standby
values were 0x11 for core 0 and 0x1 for core 1. These are observations of the
pinned control/standby fields, not electrical power-off acknowledgments.

The retained guard skipped both absent-firmware callbacks with zero callback
resumes. ABOX remained runtime-suspended and the system PM reference was
balanced. This single cycle does not establish repeated stability, full DMA
quiescence, hardware ownership handoff or XNU execution. The next source review
examines DMA status and the existing clock-held disable path; it must not add
peripheral reads while the device is runtime-suspended.


## v27 bundled domain-status extension

Evidence version 2 preserves the core frames and failed-firmware guard and adds
`N10PDS1` as a separately required fifteenth evaluation in the same boot.
The exact Exynos9820 CAL local table and its including `cal_data.c` are pinned.
Sixteen public-DT domains are covered: AUD, NPU0/1, DPU, DSPM/S, G2D,
EMBEDDED_G3D, ISPPRE/HQ/LP, IVA, MFC, VTS, FSYS0A and VRA2. Each has an
explicit configuration and status offset and bit-zero mask from the vendor
CAL write/read definitions. The DT binds PMU_ALIVE at 0x15860000 (64 KiB),
which contains every allowlisted field. No peripheral MMIO or inferred
adjacent status register is used.

After the existing complete ABOX device/tuple validation, the observer uses
`exynos_pmu_read` to sample configuration, status and configuration again for
each domain. It records three 16-bit bitmaps, not an atomic shutdown claim.
Changed configurations and status/control mismatches remain visible. A read
failure invalidates the complete observation, including zero-valued fields.
Four checksummed copies per phase are emitted; two matching copies for every
phase and the existing generation binding are mandatory. Real PMU and
SOC_EXYNOS9820 configuration plus both Image markers must match metadata and
package evidence version 2 before installation. The domain table is checked
against the pinned CAL source and actual C allowlist before building.

The combined actual-C model passes 88 scenarios, including every one of 54
read failures (six existing core reads plus 48 domain reads), mixed status and
configuration bitmaps, failed reads, lifetime/lock errors and stale, missing,
corrupt or malformed evidence. Full PC regression passes 239 tests; retained
ABOX 105, UFS/HCI 42 and IOMMU 25 source/model digests remain unchanged. Power
requests, PMU writes and clock changes are absent. A sampled-off domain still
does not prove global DMA quiescence, repeated stability or XNU execution.


The one fresh v27 physical cycle, source `073c069482a25207cd4a348d3db1290804cb64bd`
and CI `40598642972`, passed all 15 evaluations, automatic TWRP recovery and
five expected partition hashes at preinstall battery 49%. All four core/domain
frame copies were intact in all phases. Before and during devices-only suspend,
the configuration-before/status/configuration-after bitmaps were each 0x4000:
FSYS0A was sampled on and the other 15 domains were sampled off. After resume,
the three bitmaps were each 0x4080: EMBEDDED_G3D and FSYS0A were sampled on.
No configuration change was detected across any per-domain sample. Sequential
samples remain non-atomic and do not establish global DMA quiescence.

The pinned FSYS0A DT uses `power-down-ok = <3>`. The original power-domain code
maps that policy to `exynos_pd_power_down_ok_usb`, which returns
`!otg_is_connect()` with the actual USB configuration enabled. The domain's
power-off callback can skip its control operation when this predicate rejects.
This is a source-based candidate explanation, not an observed callback result.
The next diagnostic should trace the existing predicate result and skip/control
path without forcing power-off or calling the predicate an extra time.


## v28 passive FSYS0A policy trace (physical result pending)

Evidence version 3 retains all preceding observations and adds `N10FSP1` as
an independently required sixteenth evaluation. The pinned complete original
power-off callback is instrumented at entry/exit, skip, both existing control
returns and successful completion. Its existing predicate is wrapped to record
its single original result; no extra predicate call, power request, register
access, reference adjustment or forced action is added. The original retry
path is preserved exactly, including all original returns.

A matching FSYS0A owner is initialized after successful genpd initialization
and before publishing its provider. The immutable target identity includes
CAL ID 0xb138000e, name pd-fsys0a, the original control pointer and USB predicate
pointer. Replaced/foreign target identity, multiple owners, missing or repeated
initialization and counter overflow invalidate the observation. The helper
records only numeric shadow history under a short IRQ-preserving spinlock.
It never holds that lock while calling a predicate or power control function.
Captures copy the shadow history and never dereference or change the domain.
The original driver's target remains allocated for the pinned built-in lifetime.

Every phase reports initialized/invalid flags, entry/exit and gate/allow/deny,
skip/control/error/completion counts and the last control result/sign/skip flag.
A predicate that was never called stays distinguishable from a predicate that
allowed or denied power-off. Inflight callbacks and sequential samples remain
visible; the trace is not evidence of global DMA shutdown. Four copies per
phase are generation-bound; two consistent copies, bounded coherent counters
and monotonic history across phases are mandatory. Source/config/Image and
pair/record/embedded package contracts require evidence version 3, real PMU,
Exynos9820, built-in Exynos power domains and the actual Exynos USB driver.

The real-C model executes 24 scenarios for the entire original, instrumented
and disabled-instrumentation callbacks, comparing predicate, control, forced
retry, callback return and skip-flag behavior. It also executes the pinned USB
and OTG predicate bodies and checks IRQ/lock preservation, missing/foreign or
duplicate owners, overflow, signed results, mixed histories and copy isolation.
The PMU 88 scenarios still pass. Full regression passes 244 tests, including
malformed nested models and missing/corrupt/conflicting policy evidence. The
maximum policy payload is 313 bytes inside its 384-byte buffer. The retained
ABOX 105, UFS/HCI 42 and IOMMU 25 implementations and DMA hook are unchanged.
