# v141 display admission result

The v141 source at `fccbf0792c678c71b3a03634d9264a4641b1fc2e` passed its NEW-only validation and CI run `42240738427`. The CI artifact was received once and the `Image` hash was computed once. The previously reviewed NEW-only test result is carried forward; it was not rerun for this result.

One physical cycle was consumed: one BOOT write, one host reboot, one internal load, and one internal reboot. The device returned to TWRP, and all five partition checks passed before and after. No XNU entry or full boot was observed. The evidence contains five typed owner-terminal witnesses and supports only per-owner terminal predicates; it does not establish physical clock-off, all-master quiescence, or reset cause.

The next blocker is the IOMMU owner gate: `iommu-owner` returned errno `-2` for owner `18200000.iva`; controller `18020000.sysmmu` reported `active=1`, `runtime=0`, `effective=0`.
