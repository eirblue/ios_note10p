# CPU0 RCU context audit

The default-off audit reads a bounded set of local RCU and current-task software fields once in the existing owned CPU0 notifier-chain walk. It reports normalized observations only, including watching state, nesting class and positive two-increment headroom. It does not emit task pointers, raw counters or RCU internal addresses.

The reads are separate, not an atomic snapshot. The registration lock protects the notifier list; it does not protect the observed RCU fields. Successful collection means that the observation was valid in its stated context, not that CPU-PM callbacks are safe or that the state will remain unchanged. NMI, FIQ, debugger and arbitrary mutation remain outside the ordinary serialization assumption.

No CPU-PM callback, RCU enter or exit, RCU read-lock operation, hardware register access or state repair is introduced by this audit. Synthetic native and worker models are not kernel ABI or hardware evidence; actual prepared kernel compilation is required. Full hardware restoration, sampling continuity, global DMA quiescence, XNU execution and iOS boot are not established.
