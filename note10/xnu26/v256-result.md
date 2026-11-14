# v256 result

Five new PC-only predicates and one analysis of retained authenticated disassembly passed. The local outgoing arguments at the witnessed `cpu_switch_to` call map to the provider's two entry arguments only under both conditions:

- Entry registers contain `prev` and `next` according to the provider interface; upstream caller values are unproven.
- Ordinary returning helpers preserve the relevant callee-saved registers under AAPCS64; their bodies and compliance were not verified.

The analysis covered 61 instruction rows, 58 before the backend boundary, and three ordinary helper contracts. Unconditional argument flow, backend implementation, cross-object linking, switch/resume behavior, SP peak and whole-scheduler bounds remain unproven. Runtime observation and physical readiness remain false.

No new CI, compilation, native-object read, previous provenance/test replay or device operation occurred.
