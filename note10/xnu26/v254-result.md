# v254 result

The PC-only `__schedule` provenance and context-switch call-site analysis passed, with five new synthetic predicates.

The authenticated fresh object reports 112 bytes of compiler static stack usage for `__schedule`. Its call relocation and instruction agree on the external `__switch_to` boundary; 93 selected relocations and 59 transfer-frontier entries were preserved.

This establishes fresh-object evidence only. Original Image equivalence, historical compiler identity, SP peak, complete control flow and whole-scheduler stack bounds remain unproven. The switch implementation and switch/resume behavior remain opaque; physical readiness is false.

No new compiler, CI, Image/PID1 build, device operation or old test replay occurred.
