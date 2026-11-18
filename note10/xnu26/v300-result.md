# v300 watchdog refusal diagnosis

**Diagnostic PASS.** Source `663fe4b506b0f360fcf71c439a0c4395caccd206`; CI run `44235924012` succeeded. The new reason-mapping bundle passed 2 groups, 29 variants and 29 assertions. One reviewed cycle used one BOOT write and one host reboot; RECOVERY was unchanged.

The candidate reached TWRP PID1 and materialized its rootfs. The read-only snapshot isolated the refusal: the configured initial timeout was 30 seconds, while the guard expected 15. Every other driver condition and every outer readiness condition passed. No trigger process ran, no watchdog was opened, and no marker was prepared.

The unchanged 90-second software recovery request was checksum-verified. A distinct normal recovery epoch returned, all five partition checks passed, and TWRP and panel brightness read back 10. This identifies an admission mismatch; it does not prove watchdog reset, raw reset cause, XNU execution or recovery after Linux loses control.
