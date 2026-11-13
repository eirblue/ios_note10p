# v238 OF Frame and Property Frontier

## Result

The v238 fixture passed 1 group, 38 variants, and 38 assertions. One full Image/PID1 CI build succeeded, followed by one authenticated artifact GET and one Node OPEN. The Image is 50,401,292 bytes, the linked extent is 57,098,240 bytes, and the PID1 ELF is 7,728 bytes. Linked non-init growth versus the installed v229 baseline is zero.

All four borrowed-slot comparisons passed: the SP delta was zero, with caller frames of 64, 48, 48, and 48 bytes. Two property C bodies were captured, each with a 48-byte compiler frame; three property-local bodies were also captured. This is bounded static evidence and does not establish a whole call-chain bound.

The remaining external target is `preempt_schedule`. No unresolved or indirect transfer remained in the reviewed evidence. Local-SP/query-peak and runtime-hook authority remain unproven.

## Execution

The reviewed source was published to `main`. CI completed successfully once, followed by one authenticated receive. No package or device action occurred. The installed v229 baseline remains current, and the battery hold remains active.

## Scope limits

This result does not establish runtime hook behavior, local-SP/query-peak bounds, whole OF or scheduler stack bounds, or physical readiness. No device query, BOOT write, reboot, or runtime CPU observation occurred.