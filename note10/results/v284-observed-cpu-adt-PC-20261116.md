# v284 observed-CPU ADT composition (PC only)

A new composer joins a bounded FDT CPU description with an explicitly pinned guarded Linux CPU observation. It selects the unique matching firmware affinity rather than raw MPIDR flag bits, adds sampled running state and the observed little-endian timebase only to that CPU, and preserves all remaining CPU descriptions. The existing translator and canonical ADT codec are unchanged.

Both new validation variants passed in one batch: synthetic positive/refusal cases, followed by one private retained-input composition consumed by the unchanged v230 C metadata projector. One host compiler invocation and one C fixture process produced the 1,152-byte boot arguments, 64-byte adapter record and 96-byte numeric placement. No previous test suite or ABI oracle was replayed.

The retained inputs come from different captures. Same-boot FDT association, complete platform ADT, final CPU ownership, handoff readiness and hardware readiness remain false. No arm-io/GIC contract or memory ownership was inferred. Real input data and generated reference bytes remain private.

No Linux Image rebuild, CI dispatch, package rebuild, device query, partition write, reboot or XNU execution was performed. The previous native carrier and restore package remain unchanged. Parent source/result commit: `d6a407df3c6bc42b5b6098c825fbf80b3354de79`.
