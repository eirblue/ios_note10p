# GICv2 mapped-window adapter

`gicv2_mmio.c/.h` connects the existing callback-based GICv2 component to volatile 32-bit
accesses through caller-owned virtual mappings. It supports little-endian AArch64.
It never maps a physical address itself or treats a DT physical address as a valid C pointer.

## Access policy

- Validate non-null, aligned, non-overlapping distributor/CPU ranges of at least 0x1000 bytes,
  including integer overflow checks. Binding performs no register accesses.
- Read distributor CTLR/TYPER/IIDR and CPU CTLR/IAR/IIDR only.
- Write PPI/SPI enable-set/clear words and CPU EOIR only.
- Reject SGI enable writes, IDs 1020–1023 in enable masks and EOIR, reserved EOIR high bits,
  unaligned/out-of-range offsets, unsupported bank values and all CTLR writes.
- Use `DSB SY; ISB` with a compiler memory clobber for the core's ordering callback.

The immutable view and mappings must outlive every callback. The future kernel caller must provide
Device memory attributes, mapping ownership, correct security/CPU context, IRQ synchronization and
fault handling. Numeric range checks do not prove a virtual address is mapped. A hardware abort on
an invalid/inaccessible mapping cannot be converted to a callback error by this component.

This adapter does not initialize distributor/CPU control, priorities, routing, trigger modes or
security groups. It does not install an IRQ vector or provide XNU mapping APIs.

## Actual validation

`test_gicv2_mmio.c` runs the actual adapter on SM-N976N using two ordinary C arrays owned by
the Android test process. It does not open `/dev/mem`, access hardware registers or use the DT bases.
DSB/ISB instructions execute, but their behavior for real Device-mapped hardware is not established by this test.

- All byte offsets 0..0x10ff for read/write banks, plus invalid bind/range/bank/mask conditions.
- Core+adapter probe, every PPI/SPI enable/disable position, SGI source-token completion,
  special IRQ rejection and invalid-view errors.
- **30,166 assertions passed.** Temporary device executable removed.
- Freestanding ARMv8.2 ELF and Apple arm64 Mach-O objects compile; no undefined symbols.
  ELF disassembly confirms DSB SY and ISB in the synchronization callback.

The arrays record written values. They do not simulate hardware W1S/W1C state changes,
interrupt delivery or Device memory attributes. Earlier mock-register tests cover the core's
write-one semantics separately. Neither test is evidence of real IRQ handling or XNU boot.

Build: `./note10/platform/build.ps1`. Device execution is separate.
Result and test executable hash: `note10/private/gicv2-mmio-test-result.json`, `gicv2-mmio-build.json`.
