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
