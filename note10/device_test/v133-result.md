# Note 10 v133 result

The v133 source was published at commit `9b68415369cb498560b5f922cc9dc6d14f92b578`; CI run `42113581397` passed. The corrected new-only SCORE test passed after a fixture-only compile correction. The initial fixture invocation stopped at compilation (one compiler invocation, no test process); the corrected remaining cases ran once. Previously passed checks were not replayed.

Packaging consumed the retained compressed kernel member once. It read no raw kernel or adapter source and performed no recompression.

The first physical approval entry was rejected before device operations because required approval metadata was incomplete. The corrected entry admitted one physical cycle, which is now spent. It made one host BOOT write attempt and one reboot attempt. Five-partition integrity checks passed before the write and again after the write before reboot.

A fresh recovery return and the five post-return integrity checks were not confirmed within the 240-second budget. A later read-only check failed on its first ADB command before integrity checks or log collection; it made no BOOT write, reboot, or partition mutation. The timeout and failed check do not establish that recovery was absent or identify a cause. The original physical cycle produced no post-return observation, so XNU entry and a full XNU boot are not established. A watchdog reset cause is also unverified. The physical cycle must not be replayed.

## Manual recovery and restart follow-up

After the initial result, the user confirmed a manual return to recovery. A read-only check confirmed a fresh recovery session and the current v133 BOOT; all five current integrity checks passed. A later check, after the user reported two manual restarts, confirmed the same current recovery and integrity state. These checks made no BOOT writes, reboot attempts, or partition changes. The reported restart count is not device-side attempt evidence, and neither check establishes automatic return during the original 240-second wait. An optional pstore read was unavailable; collection completed.

The single-section retrospective parser returned no qualified marker because repeated begin records made that section ambiguous; the later logical sections cannot be tied to the original physical cycle or any reboot epoch. These later checks do not establish XNU entry, a full XNU boot, or a watchdog reset cause.

## Retrospective PID1 compatibility finding

A source-bound offline test passed 21 cases. The retrospective parser read one saved capture once and produced two qualified logical sections; it did not perform device operations. The captured PID1 producer emits the `N10XNU132` prefix, while the v133 native-kernel records and host consumer use `N10XNU133`. This is a host-side prefix compatibility issue in interpreting saved PID1 records, not evidence of a new device run.

Each logical section contained PID1 begin, parcel-ready, kexec-load-once, and kexec-reboot-once records, followed by a SCORE halt refusal with errno `-110` and a TS-halt detail. No final hook or recovery-fallback record was observed in those sections. The section boundaries are logical log sections, not proven boot epochs; no cross-section attempt count was inferred. They do not establish physical XNU entry or its absence, the outcome of the original return timeout, or a watchdog reset cause.