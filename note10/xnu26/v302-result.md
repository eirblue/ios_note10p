# v302 IRQ-off watchdog return qualification

**Adjudicated qualification PASS.** Source `7dc39aa509a4fb5e21d7d98c0691c06833f11c5e`; CI run `44255656812` succeeded. The new source bundle passed 2 groups, 20 variants and 20 assertions. One cycle used one BOOT write, one host reboot and one watchdog open; RECOVERY was unchanged.

Candidate TWRP/rootfs and PID1 passed admission. After the checked 10-second watchdog acknowledgement, 16 checksummed records confirmed CPU0 and all eight online CPUs had reached the IRQ-disabled rendezvous. CPU0 then entered the compiled nonreturning spin with its MMU unchanged. Normal TWRP returned before the conservative software deadline; no bound software-return phase appeared. All five partition checks passed, and settings and panel brightness read back 10.

The original physical result remains FAILED because its parser mistook later truncated quotations for direct records. A new offline check distinguished the complete direct records from those echoes and adjudicated the qualification without another device operation. This proves the bounded IRQ-off park return, not MMU-off return, CPU power-off, raw reset cause, native execution or XNU recovery. Software abort and the 90-second worker were unavailable after park entry.
