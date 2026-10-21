# Explicit Exynos compile profile

Patch 0005 adds `pexpert/arm64/EXYNOS9825.h`, selects it in `board_config.h`, and adds an Exynos
cache-line branch to `arm64/proc_reg.h`. It is a parameterized single-CPU compile profile, **not a
measured hardware profile or complete board port**. No cache/page values are provided by default.

Required inputs are `N10_BOARD_SCHEMA=1`, `N10_ICACHE_LINE_LOG2`, `N10_DCACHE_LINE_LOG2`,
`N10_MAX_CACHE_LINE_LOG2` and `N10_KERNEL_PAGE_SHIFT`. Cache-line exponents must be 4–11;
the maximum must cover both line sizes. Page shift must be 12 or 14. Accepted syntax/ranges do not
prove physical support. Defining these macros manually is not hardware validation.

`MAX_CPUS=1` and `MAX_CPU_CLUSTERS=1` restrict the software bring-up path; they do not describe all
eight physical cores. PAC/BTI kernel instrumentation, Apple CPU/platform flags, GICv3, Apple generic
timer, XNU monitor and SPTM configurations are rejected. The header does not include Apple's common
CPU header or assert Apple register interfaces, IO coherency, cache policies or PA/VA geometry.
MASTER options, platform support replacement and the actual boot contract remain incomplete.

## Real-header compilation

```powershell
python note10/xnu26/prepare_irq_bridge.py
python note10/xnu26/prepare_irq_bootstrap.py
python note10/xnu26/prepare_board_profile.py
python note10/xnu26/test_board_profile.py
python note10/xnu26/validate_series.py
```

The test uses the same pinned public source and foreign VMAPPLE generated-header inputs described
in [HEADERS.md](HEADERS.md). Patched board/proc and platform prototype headers overlay pristine inputs.
There are no replacement kernel structs or fabricated missing declarations.

- 22 header cases check positive synthetic configurations and rejected missing/conflicting inputs.
  `ARM_PGSHIFT`, instruction/data lines and single-CPU restrictions are checked against requested values.
- The **complete bootstrap and IRQ bridge C files** compile to four plain ARM64 Mach-O objects using
  synthetic page shifts 12/14. These are sample inputs, not phone-derived values.
- The component compile uses pexpert's `PEXPERT_KERNEL_PRIVATE` and `meta_features.h`. An initial
  missing `ml_io_map` declaration was caused by the diagnostic command omitting this private flag;
  no declaration workaround was added to the source.
- `-mno-implicit-float` permits real headers' NEON type declarations while avoiding implicit FP use.
  Disassembly is checked for vector/FP registers. `-mgeneral-regs-only` is unsuitable for these
  real headers with this Clang version because it rejects their NEON type declarations.
- All five patches / 17 unique files apply and reverse sequentially in isolation; public sources remain intact.

Compiling the real bridge also exposed a layering problem: pexpert did not have the osfmk-private
types/accessors used by direct `cpu_decrementer` access. Patch 0003 now declares/implements
`note10_rtclock_intr` in `arm/rtclock.h` / `rtclock.c`. The bridge calls that function; it marks the
cached decrementer expired within osfmk and calls the normal `rtclock_intr`.
The synthetic bridge/integration tests compile the actual added wrapper function and preserve the
mask → expired bookkeeping → callback → EOI → unmask sequence. The entire `rtclock.c` unit has **not**
been compiled or linked in this step.

Reports/objects/disassembly: `note10/private/xnu26-board/`. The report records patch/source/object/log
hashes, commands, synthetic inputs and `hardware_values_verified=false`. No executable kernel, boot
image or device operation is produced. Four small objects do not establish full-kernel linkage or ABI.
