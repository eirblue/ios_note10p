# v250 Compiled Caller Guard Proof

The new synthetic suite passed once: 1 group, 8 variants and 8 assertions. One offline analysis of the authenticated v241 evidence also passed. The target remains source `e07129664f1475b9576c45aa0ec44511ea6e9f53`, CI run `43413072923`; v250 did not rebuild the v241 target or execute it on-device.

For the captured `n240_observe_current_cpu` caller, every supported local control-flow path preserves the witnessed preemption-counter base at its accesses, keeps the CPU/node observation calls inside the acquired interval, and reaches the explicit scheduler call only after release. Unsupported register semantics, live-base aliases, counter-base clobbers and invalid acquisition/release paths fail closed. External calls remain opaque; the local analysis assumes the normal callee-saved register ABI and does not prove callee register or counter preservation.

This result does not establish a whole-query or scheduler stack bound, runtime admission, interval duration, or physical readiness. No CI, kernel build, package, device query, partition write or reboot was performed for v250. The missing scheduler body/object/stack evidence remains the next PC-only frontier.
