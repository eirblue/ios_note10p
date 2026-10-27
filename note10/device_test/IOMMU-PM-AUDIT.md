# Registered Exynos IOMMU PM inventory

The opt-in UFS/HCI diagnostic build also enables a default-off
`NOTE10_IOMMU_PM_AUDIT` observer when `EXYNOS_IOMMU=y`. This bundles compatible
items in one boot: reserved RAM access, XNU data staging, CPU/cache roundtrip,
per-CPU timer/PM/GIC tests, DMA framework coverage, UFS driver/HCI observations
and the registered IOMMU inventory. Each has its own strict result; every
required item must pass before the cycle is accepted. The collector writes an
`evaluation_items` map as well as the overall diagnostic result.

The IOMMU observer runs at all three existing owner/generation-bound PM capture
points after the PM device-list mutex is released. `driver_for_each_device`
holds device references. Each visitor takes a nonblocking device lock, checks
the bound driver and drvdata/device association, then copies fields under the
existing controller spinlock with IRQ flags restored. Any enumeration/lock/
identity failure, invalid counter, long name, missing controller or more than
64 registered controllers fails the observation. No device state, activation
counter, runtime PM state, page table or MMIO register is changed or read through
MMIO. No page-table or secure register address is logged.

The same snapshot includes logical activity, suspended flag, runtime-control
activity, manual runtime-control enabled/disabled counts, boot runtime holds,
secure-base configured flags, nonzero page-table flags and PM framework
syscore/prepared/suspended/runtime state. Inventory count and name digests must
remain stable across phases; name digests are not collision-proof identity
proof. Eight checksummed `N10MMU1` copies per phase are emitted, and the decoder
requires two matching copies. Exact begin-to-completed generation advance and
zero-skip wrap are checked. The actual C observer and producer, pinned driver
inline helpers and generated unlocked PM hook are executed in 21 native cases.
The existing UFS/HCI 42-case native model remains part of the same build.

The pinned Exynos system sleep callback is registered for the late stage.
A devices-only test does not establish that it ran. Active IOMMU observations
are valid inventory results, never successful hardware-shutdown claims. This
covers registered driver instances only, collected sequentially, and does not
prove unregistered hardware coverage, a globally atomic snapshot, DMA shutdown,
secure-world isolation or XNU execution. The combined build completed its own full compilation and fresh physical
cycle with automatic recovery and five-partition integrity. Raw captures and packed BOOT images stay private.

Source `1995d9348d57a0557c6c460697eb4dd25fda7e21` passed full kernel build
[40443986097](https://github.com/eirblue/ios_note10p/actions/runs/40443986097).
All nine required diagnostic categories passed in one physical boot, together
with fresh automatic TWRP return and all five partition hashes. The actual
IOMMU C model passed 21 cases, UFS/HCI passed 42, and host regression passed 181.
Logical IOMMU activity remained at the devices-only suspend boundary.
These results do not establish hardware IOMMU/DMA shutdown or XNU execution.

## Selected identities and policy predicate (version 2, physical test passed)

`N10MMU2` retains the aggregate snapshots and adds the exact driver policy-active
count using the three pinned inline helpers. Logical activation references,
runtime eligibility and manual enable state remain separate from hardware proof.
Selected identities cover every registered controller with a runtime count,
manual-control setting, boot hold or syscore flag. At most eight identities per
phase and 63 name bytes are allowed; overflow fails instead of truncating or
omitting a controller. Names are hex-encoded in private `N10MMD1` records and
must decode to printable device names. No page-table or secure-base address is
recorded. Real controller names and raw logs are not published.

Four copies of each selected identity (or an explicit empty-list sentinel) are
emitted per phase. At least two intact matching copies for every index are
required. Their generation, count, policy predicate and exception coverage must
match the aggregate. Duplicate names, changed syscore identities and missing
records reject the diagnostic. When all registered controllers are selected,
their names must also reproduce the complete aggregate name digest. The bounded
report cache is static under the single reporting worker to avoid growing the
kernel stack with the identity array.

All prior diagnostics remain in the same boot. The local regression suite
passed 185 tests, and 25 actual-IOMMU-C cases cover normal and error paths,
zero-selected and 64-registered inventories, exception/name bounds, ambiguous
names, IRQ/reference restoration and the exact pinned policy helpers. Version 2 completed its own full kernel build and fresh physical evaluation.

Version 2 source `188c8339b7afccf5da5fa4f6bd4f084434dcd38b` passed full kernel
build [40447515344](https://github.com/eirblue/ios_note10p/actions/runs/40447515344).
The fresh combined physical cycle passed every required evaluation, automatic
TWRP return and all five partition hashes. The selected runtime/syscore/manual
controller identities matched their aggregate policy counts and remained private.
Host regression passed 185 cases and the actual IOMMU C model passed 25.
At the devices-only boundary, 1 selected controller identities and 1 policy-active instances were observed.
This policy observation does not establish hardware DMA/IOMMU shutdown or XNU execution.
