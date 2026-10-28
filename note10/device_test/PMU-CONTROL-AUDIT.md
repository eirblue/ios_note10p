# CPU0 PMU control observation

The default-off diagnostic observes a bounded set of EL1-visible PMU control values during the existing owned CPU0 notifier-chain walk. It requires exactly one PMU notifier and the expected ARMv8 backend, validates the target identity, and uses one nested nonblocking PMU lock. It does not invoke CPU-PM callbacks, read event counters, change selectors, or write registers. The observer clears its temporary PMU candidate before releasing the notifier-chain lock.

A successful observation makes four additional identity reads and three additional PMU control reads. The existing context checks may perform their own reads. Disabled or unequal enable masks are valid observations, not evidence that a CPU-PM callback is safe. PMCR.N and enable masks are EL1-visible values; higher-level counter restrictions such as HPMN can hide counters and prevent conclusions about all physical counters or interrupts.

Architectural access relies on the explicitly inherited unchanged higher-EL and security regime. The diagnostic does not observe that regime, prove access is trap-free, or catch a synchronous register-access exception. Native source and protocol models use synthetic registers and structures; they do not establish hardware behavior. This diagnostic does not call CPU-PM or execute XNU.

## Validation

The build at source `ca2260145601a65cf82fd9177a2a702c0daafd5a` passed [CI 40760960052](https://github.com/eirblue/ios_note10p/actions/runs/40760960052), including 20 source, configuration and model bindings. PC models use synthetic registers and structures.

One physical diagnostic cycle passed all 39 evaluations, returned automatically to TWRP, and passed the five partition integrity checks. Battery was 52% immediately before installation; TWRP and panel brightness both read back as raw 10 after recovery. This observation does not establish complete hardware restoration, safe direct CPU-PM execution, or XNU execution.
