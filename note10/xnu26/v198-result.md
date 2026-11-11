# v198: USER64 exception fetch caller

The host policy fixture passed all 24 cases across three groups. The reviewed source commit was `f7b67b0b82b99739a6e2dfd310fc01a4a15e6e09`. Its single CI run was `42972445207` (attempt 1).

The CI run compiled the changed real USER64 exception caller successfully. It then failed during the bounded object symbol-validation stage with a `ValueError`; the exact cause is not yet established. The authenticated result was received once. No retry or follow-on native join was performed.

This result does not establish a full kernel build or link, runtime ownership or copyin, a user mapping, executable admission, activation, launch, or physical behavior. No device action occurred.
