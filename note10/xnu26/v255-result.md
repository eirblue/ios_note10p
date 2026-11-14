# v255 result

The PC-only fresh `__switch_to` provider analysis passed, with four new synthetic predicates and one [object-only CI build](https://github.com/eirblue/ios_note10p/actions/runs/43531733946) under the exact retained configuration and Android 11/r environment.

Authenticated compiler evidence contains a complete 244-byte provider and reports 32 bytes of static stack usage. Its relocation and BL instruction agree on the external `cpu_switch_to` boundary.

The backend implementation, numeric context offsets, argument-register flow, cross-object link resolution and switch/resume contract remain unproven. Original Image equivalence, historical compiler identity, SP peak and whole-scheduler stack bounds also remain unproven; physical readiness is false.

No Image/PID1 build, device operation or old test replay occurred.
