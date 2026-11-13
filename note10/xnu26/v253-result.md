# v253 result

The PC-only scheduler provenance step passed on commit `23c9584a398837cf162b6df211fecdd8c78b5099` ([CI run 43522290674](https://github.com/eirblue/ios_note10p/actions/runs/43522290674)).

Restoring the Android 11/r build environment reproduced the exact baseline configuration. Authenticated object evidence matched the retained machine-code bodies of `preempt_schedule` and `preempt_schedule_common`. Their fresh compiler-reported static stack usage was 16 and 32 bytes, respectively; this does not establish historical compiler identity or a complete call-chain bound.

The remaining frontier is `__schedule`, context switching, IRQ and NMI handling. Whole-scheduler and whole-frontdoor stack bounds remain unproven, and physical readiness remains false.

No full Image/PID1 build, device operation, new fixture run or old test replay occurred.
