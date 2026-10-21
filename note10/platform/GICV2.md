# GICv2 interface components

`gicv2.c/.h` is a freestanding callback-based register access component, not a complete initialized
Note10+ interrupt controller driver. It contains no physical addresses or direct MMIO accesses.

Firmware DT evidence identifies the candidate distributor at 0x10101000 and CPU interface at
0x10102000. These are declarations from the supplied HXJ2 firmware, not live observations.
The existing V60 GICv3 redistributor/system-register path cannot substitute for these interfaces.

## Implemented

- Read TYPER and distributor/CPU ID registers; derive an IRQ count bounded by 1020.
- In an already initialized EOImode=0 context, read IAR and retain the entire acknowledged token.
- Treat IDs 1020–1023 as special without writing EOIR.
- Complete a valid token through EOIR, retaining SGI source-CPU bits.
- Enable/disable PPIs and SPIs using write-one set/clear registers; avoid read-modify-write.
- Reject malformed parameters and split-deactivation mode. Ordering is an explicit mandatory callback.

An IAR read changes controller state; a later error cannot undo acknowledgment. Similarly, a failed
ordering callback after EOIR or an enable write does not imply that the write was rolled back.
Output structures are preserved on unsuccessful reads, but hardware side effects are not transactional.

No distributor/CPU initialization, security-group assignment, priority/trigger/routing configuration,
SGI generation, token lifecycle tracking, SMP locking or exception-vector installation has been implemented.
A bounded MMIO/barrier adapter has since been added; see [GICV2-MMIO.md](GICV2-MMIO.md).
The future kernel caller must enforce same-CPU token completion order,
ownership, Device memory mappings and appropriate barriers. Register ID snapshots alone do not
establish usable non-secure interrupt ownership.

## Validation

On the connected SM-N976N, an Android executable tested **mock registers in its own process memory**:

- 1,132 acknowledge/EOI tokens, covering all ordinary INTIDs and eight SGI source-CPU encodings.
- All 32 TYPER count fields and special IDs 1020–1023.
- All PPI/SPI set/clear positions, preserving neighboring enabled bits.
- Unsupported mode, malformed input, injected read/write/order failures and partial-side-effect checks.
- **10,856 assertions passed.** The device's actual GIC registers were never accessed.

The test executable was deleted from the device. Results/build hash remain under
`note10/private/gicv2-test-result.json` and `gicv2-build.json`.
Freestanding ARMv8.2 ELF and Apple arm64 Mach-O objects compile with warnings treated as errors.
This is not evidence of real timer interrupts, XNU linking or native boot.

Build: `./note10/platform/build.ps1`. Device execution is separate.

Register definitions and independent behavioral reference:
[Linux v6.12 arm-gic.h](https://raw.githubusercontent.com/torvalds/linux/v6.12/include/linux/irqchip/arm-gic.h),
[Linux v6.12 GIC driver](https://raw.githubusercontent.com/torvalds/linux/v6.12/drivers/irqchip/irq-gic.c).
The component is independently written; Linux driver functions are not embedded.
