# v217 source ownership accounting

The reviewed source was published to `main` at [`5fa896a`](https://github.com/eirblue/ios_note10p/commit/5fa896a2baf51bf8c166e9a34b3294a1dc90122c). [CI run 43213907547](https://github.com/eirblue/ios_note10p/actions/runs/43213907547) failed at a profile guard before the target compile.

The host fixture passed 10 groups, 18 variants, and 37 assertions.

The guard reported that a required prepare/return setting had changed. The effective configuration was not saved before the guard, so the specific setting and root cause remain unconfirmed. No target object, Image build, PID1 link, or RAM accounting result was produced.

No device query, BOOT write, or reboot occurred. v208 remains the last verified installed baseline. The v217 source does not establish native ownership or hardware readiness.
