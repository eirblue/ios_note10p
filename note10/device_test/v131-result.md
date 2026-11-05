# Note10 v131 terminal DMA result

- Source: `558c814fe5fb983a919c0dbd5b31e50ad7dd3b6e`.
- CI: one run completed successfully; the sealed build artifact was accepted once.
- New gate checks: the first run exposed a fixture-only failure. One corrected run of the remaining new gate cases passed. Existing tests and spent physical cycles were not replayed.
- Packaging reused the retained compressed payload once, with zero raw kernel reads, adapter reads, or recompressions.
- Physical cycle: one BOOT write and host reboot; one internal load and reboot attempt; automatic return to fresh TWRP; all five partition integrity checks passed before and after. The cycle ended safely without qualifying the final hook or observing XNU entry or a full XNU boot.
- The saved refusal occurred at the IOMMU owner safety gate because a graphics DMA owner could not be proven idle. USB and UFS gates appear to have passed because execution reached the later IOMMU stage; this is an inference from source order and the saved refusal, not a separately persisted USB/UFS success witness.
- No retry is allowed for the spent v131 cycle.

This public summary excludes device identifiers, owner addresses, boot arguments, logs, images, backups, and keys.
