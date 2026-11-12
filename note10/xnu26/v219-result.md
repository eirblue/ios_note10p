# v219 fixed source request budget

The reviewed source was published to `main` at [`f748645`](https://github.com/eirblue/ios_note10p/commit/f748645621404256dfd9a1b2669ac1b98d1393e8). [CI run 43228015096](https://github.com/eirblue/ios_note10p/actions/runs/43228015096) failed during the target owner-object compile.

The carried host fixture passed 7 groups, 14 variants, and 25 assertions; it was not rerun for this publication. The new context metadata fixture passed 1 group, 3 variants, and 3 assertions. The SHA oracle tests passed separately.

The target compile reported four uses of `__attribute__((noinline))` that collided with the stock compiler’s `noinline` macro. Failure evidence was authenticated and received locally. No owner object or `sizeof` result was produced, so no accounting report was generated.

No full Image or PID1 build, package, or device operation occurred. v208 remains the last verified installed baseline. This run does not establish native request accounting or physical readiness.
