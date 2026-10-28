# CPU0 FPSIMD reference audit

The default-off reference audit classifies the CPU-local last-state reference as null, the current thread's FPSIMD state address, or another non-null reference. The third class can include kernel FPSIMD state; it does not identify another task or the physical register owner. The pointer is neither dereferenced nor emitted.

The audit runs within the existing owned CPU0, IRQ-off notifier-chain walk and compares its separately sampled software fields with the earlier FPSIMD observation. The two reads are not an atomic snapshot; mismatches and unsupported contexts fail collection. This observation does not call CPU_PM, access FP/SIMD registers, prove register preservation or authorize a later callback. It assumes the reviewed ordinary CPU/task serialization contract and does not establish the absence of instrumentation, nested execution, hotplug or higher-priority mutation.

The feature is checked by source composition, synthetic native and worker models, protocol and collection tests, and package evidence. Synthetic layouts do not establish kernel ABI behavior; the actual prepared kernel build is required for that evidence.

## Validation

The prepared kernel from source `cb568978e3fcb173593e8f3f705688ca32f36a30` passed [CI 40769141674](https://github.com/eirblue/ios_note10p/actions/runs/40769141674), including 21 source, configuration and model bindings. PC models cover the reference getter, the composed caller and the enabled and disabled reporting paths; these are synthetic tests.

One physical diagnostic cycle passed all 40 evaluations. The immediate pre-install battery reading was 47%, automatic return to TWRP and all five post-return partition hashes passed, and the TWRP and panel brightness values were verified at raw 10. This regression does not execute CPU_PM directly or establish complete FP hardware preservation, global DMA quiescence, XNU execution or iOS boot.
