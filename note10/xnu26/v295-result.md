# v295 diagnostic result

**PASS** — source `628f7d7f22222b1ea31e951f3bce6f7b7dbe674e`; CI run `44173804117` succeeded. The six synthetic compiler-proof cases passed. One reviewed physical cycle used one BOOT write and one host reboot. It observed the late-init arm, SYSTEM_RUNNING park, and checksummed 90-second software recovery request, then returned to normal TWRP. All five partition checks passed. TWRP and panel brightness read back 10; RECOVERY was unchanged.

Limits: this demonstrates cooperative recovery while Linux remains running. It does not demonstrate watchdog reset, XNU execution, or recovery after Linux loses control.
