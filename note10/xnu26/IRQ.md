# Exynos timer IRQ bridge patch

`0003-exynos9825-timer-irq-bridge.patch` packages the existing GICv2 core/MMIO adapter into the
pinned XNU reference, adds `pe_note10_irq.c`, and selects `pe_note10_handle_irq` from `sleh_irq`
only for ARM64_BOARD_CONFIG_EXYNOS9825. Other ARM64 targets see empty new compilation units.
The source file list and private platform prototypes are included in the patch.

## Implemented path

1. Caller binds already initialized, non-secure EOImode0 GICv2 Device mappings and an explicit timer PPI.
2. The binder requires single-CPU topology and masked interrupts; validates the mapped windows,
   probes the controller, checks distributor/CPU enables and EOI mode, then enables the selected PPI.
3. XNU's normal IRQ prologue runs, followed by IAR acknowledgment through the bounded MMIO adapter.
4. For the registered timer only, mask CNTP, mark the cached decrementer expired as in `sleh_fiq`,
   and invoke `rtclock_intr`. Patch 0002 selects physical TVAL for the callback's rearm.
5. Complete the exact acknowledged token through EOIR, then unmask CNTP. Normal entropy/IRQ epilogue follows.

Special IDs 1020–1023 return without EOIR or timer callback. Unbound, unsupported-source, bad-context
and I/O/mode failures panic; they are not silently acknowledged. A completion failure leaves CNTP masked.
Unknown SPIs/SGIs have no dispatch implementation yet. The bridge handles one acknowledged interrupt per entry.

The new CTLR check only reads registers. It does not initialize control, groups, priority, routing or triggers.
The MMIO adapter now allows read-only distributor CTLR observation; CTLR writes remain forbidden.

## Validation

`prepare_irq_bridge.py` pins five existing source files by SHA-256, generates ten changed/added
files, checks the patch, and applies/reverses it in an isolated stage. Original sources remain unchanged.

`test_irq_bridge.py` compiles the actual bridge, GIC core/MMIO adapter and modified `sleh_irq` function.
Kernel types/services are test substitutes, MMIO is synthetic mapped RAM, and CNTP MSRs are intercepted
under Unicorn. This is a machine-code execution test with synthetic inputs, not privileged hardware testing.

Per-CPU expired bookkeeping now lives in `note10_rtclock_intr` within osfmk's `rtclock.c` rather than
pexpert's bridge. Tests include the actual new wrapper function. The complete bridge also compiles
against real headers with explicit synthetic board inputs; see [BOARD.md](BOARD.md).

**20 cases passed**, including:

- Correct timer: prologue → IAR → timer mask → expired bookkeeping → callback/rearm → EOIR → unmask → epilogue.
- Four special IDs; unknown SPI/SGI; missing/repeated binding; disabled controller; invalid EOI mode.
- Zero/multiple CPUs, interrupts unmasked, invalid PPI/window, and mode change during callback.
- New compilation units also pass syntax checks with the Exynos macro absent.

The CTLR-read adapter change was independently rechecked on SM-N976N using ordinary memory buffers:
**30,166 assertions passed**, temporary device executable deleted, no real GIC registers accessed.
The IRQ bridge itself was not run on the phone. Test and patch hashes are in `note10/private/xnu26-irq/`.

```powershell
python note10/xnu26/prepare_irq_bridge.py
python note10/xnu26/test_irq_bridge.py
```

## Remaining boot integration

Patch 0004 now adds a checked mapping/binding call to the boot source path; see [BOOTSTRAP.md](BOOTSTRAP.md).
It adopts an explicit pre-initialized handoff. A truthful producer must establish non-secure ownership,
EOImode0, priority mask, PPI trigger and routing before binding, with one configured CPU and interrupts masked.
The binder/bootstrap is not a substitute for GIC cold initialization, which is still missing.

Firmware suggests non-secure physical INTID 30, but runtime selection is unverified and not hardcoded.
The callback must rearm the timer; unmasking an unchanged expired deadline can immediately assert it again.
Suspend/resume, SMP/IPIs, other devices, frequency/ADT agreement and kernel build dependencies remain unresolved.
Interrupt debug classification retains the existing outer IRQ OTHER classification; timer-specific accounting
needs review before performance/debug claims.

The patch series still lacks the Exynos board header/MASTER profile and a complete linked kernel.
No actual timer IRQ, XNU boot or iOS execution has been established.
