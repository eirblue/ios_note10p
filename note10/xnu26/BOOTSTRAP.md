# Checked GIC handoff adoption

Patch `0004-exynos9825-irq-bootstrap.patch` adds the first mapping/binding call to the Exynos
`pe_arm_init_interrupts` path. It runs for non-null boot arguments after VM setup, in the source sequence
where CPU topology is already parsed. It preserves the existing call to `pe_arm_init_timer` for common
timebase setup. The unrelated legacy interrupt-controller mapping helper is excluded for Exynos.

This is **adoption of an explicitly pre-initialized GIC**, not cold initialization.
No producer currently supplies the required handoff or profile in a bootable Note10+ image.

## Input contract

The generated Apple device tree must contain `/chosen/note10-platform`. Numeric properties are
little-endian fixed-size data; `gic-reg` contains absolute physical addresses rather than arm-io offsets.

| Property | Required content |
|---|---|
| compatible | Exact NUL-terminated `samsung,exynos9825-note10` |
| version | u32 = 1 |
| gic-handoff | u32 = 1, only after a producer actually initializes/validates non-secure GICv2 |
| gic-reg | Four u64: 0x10101000, 0x1000, 0x10102000, 0x1000 |
| timer-intid | u32 = 30, candidate non-secure physical PPI from supplied firmware |
| timebase-frequency | u32 equal to runtime CNTFRQ and XNU gPEClockFrequencyInfo |

The addresses/PPI are pinned to the supplied firmware candidate configuration; real routing and
selected live DT remain unverified. Setting a handoff property is a declaration, not proof that secure
firmware/GIC ownership is correct. It must not be used to bypass missing hardware initialization.

The bootstrap requires one configured CPU and interrupts masked. It validates every property and
frequency before calling `ml_io_map` for either window. The existing XNU implementation maps with
VM_WIMG_IO. After successful mappings, it calls patch 0003's binder, which checks controller enables,
EOImode0 and ranges before enabling the timer PPI. No distributor/CPU CTLR initialization is performed.

The three-way frequency check catches the existing 24MHz fallback if it disagrees with the runtime
counter and DT. No frequency is silently changed. A missing/malformed profile, bad address, mismatch
or failed mapping panics. Failure after the first mapping is a terminal boot failure, not a transactional
mapping rollback. No cold-state recovery, suspend/resume or SMP path is implemented.

## Validation

`prepare_irq_bootstrap.py` checks the pinned source and preceding bridge inputs, generates four
changed/added files, and verifies isolated patch apply/reverse without altering reference sources.

`test_irq_bootstrap.py` compiles the actual bootstrap and modified `pe_arm_init_interrupts` function.
Kernel types, DT services, CNTFRQ, mappings, binding and common timebase services are synthetic substitutes.
The prior bridge test separately executes its actual GIC/binder/IRQ implementation with synthetic MMIO.

**20 bootstrap cases passed**: valid handoff, null arguments preserving common timebase setup,
missing/malformed/wrong properties, unexpected windows/PPI, zero/overflow/mismatched frequencies,
mapping failures, SMP and interrupts enabled. Property buffers are deliberately unaligned.
The new file also passes syntax checking with the Exynos macro absent.

`validate_series.py` sequentially applies all **4 patches / 12 files** in an isolated minimal source tree,
then reverses them and compares original bytes. This validates patch composition, not full-kernel compilation.

```powershell
python note10/xnu26/prepare_irq_bootstrap.py
python note10/xnu26/test_irq_bootstrap.py
python note10/xnu26/validate_series.py
```

Results/hashes: `note10/private/xnu26-bootstrap/` and `note10/private/xnu26-series-result.json`.
All work was on the PC; no phone files or hardware registers were accessed during this step.

An additional integrated mode links the actual bootstrap/init, binder, GIC core/MMIO adapter and
timer IRQ handler together, replacing only the surrounding DT/kernel services/registers/MMIO with
synthetic test fixtures. It covers 31 cases, including disabled controllers, both EOImode bits,
overlapping/unaligned returned mappings and timer/special/unknown IRQ handling after initialization.
The binder is not substituted in this mode. No actual memory mapping or device interrupt is tested.

```powershell
python note10/xnu26/test_irq_bootstrap.py --integrated
```

The integrated report is `private/xnu26-bootstrap/integration-result.json` and records both bootstrap
and bridge patch hashes. The 20-case service-isolation mode remains available without the flag.

## Remaining

Actual GIC ownership/priority/trigger/control initialization and a truthful handoff producer are missing.
The Exynos board header/MASTER profile, MMU/memory/boot contract, whole Darwin build environment and
real IRQ/iOS verification remain incomplete. No bootable kernel or flash package is produced here.
