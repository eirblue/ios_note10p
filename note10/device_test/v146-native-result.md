# v146 native IVA object integration

The pinned public kernel source, with the accepted v142 through v146 production overlays, compiled all four requested AArch64 native objects: iva_ctrl.o, iva_mcu.o, iva_ipc_queue.o and iva_mem.o. The CI used one stock defconfig generation and one combined object make. Previously passed host tests were not rerun.

Authenticated build evidence confirms ELF64 little-endian AArch64 relocatable outputs, the recorded compiler commands and required production helper dependencies. The effective IMA profile resolved to disabled using the generated configuration, generated macro evidence and successfully compiled production sidecar fence. No forced configuration override was used.

The single CI attempt succeeded. Its encrypted evidence was downloaded once, authenticated by the original Node transport and extracted once as 24 bounded files. Source, run, object and configuration metadata matched the reviewed contract.

This establishes target-header/API compile integration only. Full linking, kernel execution, MMIO lifetime, DMA or firmware termination and physical IVA ownership remain unproven. No Image, package or device operation occurred. The later v147 deinit change is outside this build's frozen scope.
