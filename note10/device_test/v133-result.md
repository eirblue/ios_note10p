# Note 10 v133 result

The v133 source was published at commit `9b68415369cb498560b5f922cc9dc6d14f92b578`; CI run `42113581397` passed. The corrected new-only SCORE test passed after a fixture-only compile correction. The initial fixture invocation stopped at compilation (one compiler invocation, no test process); the corrected remaining cases ran once. Previously passed checks were not replayed.

Packaging consumed the retained compressed kernel member once. It read no raw kernel or adapter source and performed no recompression.

The first physical approval entry was rejected before device operations because required approval metadata was incomplete. The corrected entry admitted one physical cycle, which is now spent. It made one host BOOT write attempt and one reboot attempt. Five-partition integrity checks passed before the write and again after the write before reboot.

A fresh recovery return and the five post-return integrity checks were not confirmed within the 240-second budget. A later read-only check failed on its first ADB command before integrity checks or log collection; it made no BOOT write, reboot, or partition mutation. The timeout and failed check do not establish that recovery was absent or identify a cause. No post-return observation was collected, so XNU entry and a full XNU boot are not established. A watchdog reset cause is also unverified. The physical cycle must not be replayed.