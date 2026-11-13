# v237 Address-Bound OF Outlined Evidence

## Result

The v237 fixture passed 1 group, 27 variants, and 27 assertions. One full Image/PID1 CI build succeeded, and the authenticated receive completed with one GET and one Node OPEN. The Image is 50,401,292 bytes, the linked extent is 57,098,240 bytes, and the PID1 ELF is 7,728 bytes.

The authenticated build evidence captured and joined 13 outlined helper bodies. None of those 13 helpers met the strict zero-own-stack rule: four reference SP directly, while nine contain calls or external transfers. The same-body `strcmp` alias was separately proven to use zero own stack (85 instructions). Remaining external targets include `of_property_read_variable_u32_array` and `preempt_schedule`; the lookup runtime bound and runtime hook remain unproven.

## Execution

The reviewed source was published to `main`. CI completed successfully once, followed by one authenticated artifact GET and one Node OPEN. No package or device action occurred. The installed v229 baseline remains current, and the battery hold remains active.

## Scope limits

This result records static selected-function evidence and the successful Image/PID1 build. It does not prove a whole OF or scheduler chain bound, lookup runtime bound, runtime hook behavior, or physical readiness. No device query, BOOT write, reboot, or runtime CPU observation occurred.