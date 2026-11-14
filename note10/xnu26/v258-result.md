# v258 result

Six new PC-only predicates and one retained-disassembly analysis passed. The finite local model accounts for 13 abstract save/load slots and symbolic SP, SP_EL0, LR and return-target origins.

This result assumes abstract entry arguments, valid disjoint aligned context memory, and fault-free execution without interference. Loaded SP/LR values remain uninterpreted saved values. It establishes local effects under those conditions; actual task/stack validity, internal C layout, liveness, switch/resume behavior, linking and whole-scheduler bounds remain unproven. No compiler stack-usage or assembly-frame bound is claimed; physical readiness remains false.

The analysis covered 21 instruction rows with 19 newly modeled suffix rows. No CI, native-object/body read, earlier proof/test replay or device operation occurred.
