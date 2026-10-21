# XNU Exynos physical decrementer selection

`0002-exynos9825-physical-decrementer.patch` targets the pinned public
xnu-12377.121.6 `osfmk/arm64/machine_routines.c`. It is a source-selection patch,
not a working interrupt-controller/timekeeping port.

## Source behavior and change

The existing `setPop` computes a relative delay from `mach_absolute_time()` and passes it to
`ml_set_decrementer`. The Exynos branch keeps **CNTVCT_EL0 as the shared timebase**
while selecting **CNTP_TVAL_EL0/CNTP_CTL_EL0 for decrementer programming and pending status**.
The private upstream KERNEL_CNTV_* macro names are retained, even where they select a physical register.
It does not mix a virtual absolute deadline with a physical CVAL register.

The Exynos enable path masks/disables both timer channels, applies the initialized per-CPU cached
decrementer value to physical TVAL, enables/unmasks the physical timer, then issues ISB.
It avoids enabling a timer with an unknown reset deadline or disabling its chosen physical timer
through the upstream virtual-only precaution. Existing generic/Apple enable paths remain.
Selecting Exynos and HAS_APPLE_GENERIC_TIMER together produces an explicit compile error.

The caller must have initialized CPU data and masked interrupts, as required by the existing
fiq_context_init/decrementer paths. CPU initialization and per-CPU synchronization are not supplied.

## Validation

`prepare_timer_selection.py` checks the source SHA-256, generates the patch, verifies git apply --check,
and applies/reverses it in a private stage. Pristine source bytes stay unchanged.

For Exynos, generic and Apple variants, it extracts the actual modified macro block and functions,
compiles/links them with NDK Clang/LLD, and executes the machine code under Unicorn. CPU-data types,
assertions and register MRS/MSR values are test substitutes, not a complete XNU environment.

- Each variant: five decrementer boundary values and eight control-bit combinations.
- All **39 execution cases passed**: enable write ordering, selected TVAL get/set, pending bit and unchanged timebase.
- Contradictory Exynos/Apple selection rejected by the compiler.
- Source fragments compile; full kernel header/ABI and link compatibility remain unchecked.

Reproduce: `python note10/xnu26/prepare_timer_selection.py`.
Results and source/patch/fragment ELF hashes: `note10/private/xnu26-timer/result.json`.
No device files were transferred or executed for this test.

## Required before actual operation

Firmware suggests non-secure physical PPI 14 / INTID 30. Runtime routing/security ownership is unverified.
GICv2 initialization, IRQ vector dispatch to rtclock_intr and EOI ordering are not connected by this patch.
The upstream HAS_GIC_V3 path cannot be reused as-is.

Timebase frequency must match actual CNTFRQ and generated Apple DT. The public source has a 24MHz fallback;
supplied Samsung firmware declares 26MHz. This patch does not substitute either value or build a matching ADT.
Counter access/offset setup, suspend/resume and multi-core behavior remain unverified.
The physical timer selection still needs privileged hardware validation.

Patch 0004 adds a runtime CNTFRQ/DT/XNU frequency agreement check before GIC mapping; see
[BOOTSTRAP.md](BOOTSTRAP.md). It does not supply a validated live frequency or construct the required ADT.

No whole XNU build, real IRQ delivery or native iOS boot has occurred.
