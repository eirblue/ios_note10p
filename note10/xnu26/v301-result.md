# v301 Linux watchdog causal qualification

**Timing-based causal qualification PASS.** Source `9b6324202be2691f4604e7ad2cd474b758fd2871`; CI run `44240987584` succeeded. The new exact-timeout bundle passed 2 groups, 8 variants and 8 assertions. One reviewed cycle used one BOOT write, one host reboot and one watchdog open; RECOVERY was unchanged.

The candidate TWRP/rootfs passed every admission condition with the observed initial 30-second timeout. One host-only actor prepared the recovery marker, set and read back 10 seconds, and held its descriptor without keepalives. A distinct normal recovery epoch was observed before the conservative 90-second fallback deadline. The bound arm/preparation records were complete, and no bound software request phase appeared across the saved logs. All five partition checks passed; TWRP and panel brightness read back 10.

This supports watchdog causality while Linux remained alive. It does not prove the raw reset cause, recovery after Linux loses control, native execution or XNU recovery. The cooperative fallback was previously proven in v300; it did not run in this cycle.
