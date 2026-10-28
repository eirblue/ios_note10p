# CPU0 FPSIMD reference audit

The default-off reference audit classifies the CPU-local last-state reference as null, the current thread's FPSIMD state address, or another non-null reference. The third class can include kernel FPSIMD state; it does not identify another task or the physical register owner. The pointer is neither dereferenced nor emitted.

The audit runs within the existing owned CPU0, IRQ-off notifier-chain walk and compares its separately sampled software fields with the earlier FPSIMD observation. The two reads are not an atomic snapshot; mismatches and unsupported contexts fail collection. This observation does not call CPU_PM, access FP/SIMD registers, prove register preservation or authorize a later callback. It assumes the reviewed ordinary CPU/task serialization contract and does not establish the absence of instrumentation, nested execution, hotplug or higher-priority mutation.

The feature is checked by source composition, synthetic native and worker models, protocol and collection tests, and package evidence. Synthetic layouts do not establish kernel ABI behavior; the actual prepared kernel build is required for that evidence.
