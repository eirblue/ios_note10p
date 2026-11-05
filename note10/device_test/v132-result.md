# Note10 v132 test result

- Source: `f98114c5c5df00f2ef0dffb7f9357bf977c184cc`
- CI run: `42093207018` (accepted)
- The new G2D terminal-proof test passed. The physical cycle completed once and returned to TWRP; the five partition integrity checks passed.
- The cycle stopped safely at the IOMMU owner gate with `ENOENT` (`-2`) for the SCORE driver class. Controller status was active `0`, runtime `0`, effective `0`.
- Effective `0` alone does not prove terminal DMA or master quiescence. The refusal stopped the reviewed handoff path. No physical XNU entry or execution was observed, and full XNU boot was not proven. The final hook was not qualified, and the watchdog reset cause was not validated.
- The retained compressed payload was read once for packaging. Raw kernel reads, adapter reads, and recompression were zero.
- This cycle was spent once; it was not retried.