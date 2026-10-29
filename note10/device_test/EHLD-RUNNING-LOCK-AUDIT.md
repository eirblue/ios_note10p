# EHLD running-state scalar synchronization

The v47 experimental `--ehld-running-lock-audit` option is off by default. It requires both the existing EHLD lock and paired irqsave audits. Its measured marker is `CONFIG_NOTE10_EHLD_RUNNING_LOCK_AUDIT`.

The source variant routes the two EHLD start/stop `ehld_running` stores through a small per-CPU control-lock helper. The helper saves IRQ state, acquires only that control lock, stores the scalar, and restores the matching state. Event creation, publication, enablement, disablement, release, logging, and MMIO remain outside the helper. The start store remains before enablement; the stop store remains after release and pointer clearing. Existing CPU-PM and raw-updater code remain unchanged.

These two stores synchronize with readers that acquire the same control lock. The earlier precondition getter still uses an unlocked `READ_ONCE` sample; the later lock getter remains a separate trylock sample. This change does not make those samples atomic, serialize the event lifecycle, or establish event readiness or lifetime.

Normal maskable IRQ and stop-IPI delivery are deferred while the helper holds its irqsave lock. Fatal exception or NMI reentry and a stopped lock owner remain conditional hazards for the existing blocking panic/hardlockup updater. This variant does not provide bounded panic completion or NMI safety, and does not change that updater to trylock.

The planned proof bundle includes exact reconstruction of the actual v46 78-file baseline, two changed kernel files with 76 unchanged, actual-function host models and negative controls, a 25th binding with the existing 24 preserved, strict off/on package scope, production package/precheck/collector models, the unchanged 27 collector regressions, and all six historical package flows. Host fixtures remain synthetic and do not prove hardware behavior.

The existing 39 collector rows and three derived rows remain unchanged: 42 total, 41 required. The physical goal is one regression cycle with automatic TWRP return, five-partition integrity, and verified raw brightness 10 before and after the cycle. No direct CPU-PM invocation, event dereference, new hardware observation, XNU execution, or iOS boot is included. The v47 build and physical test are pending.
