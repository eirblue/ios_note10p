# XNU runtime planner: verified PC-only kernel component

v55 passed [CI 41058332903](https://github.com/eirblue/ios_note10p/actions/runs/41058332903),
attempt 1, for source `9cb92b1d68bf2d80fc3a5f5cbde62193c75715f9`.
The verdict is **actual-kernel object integration plus host-wrapper evidence**.
Both disabled and enabled `arch/arm64/mm/init.o` objects were compiled using the
actual pinned Linux headers in isolated source/output trees and captured before
proof acceptance. The result binds 11 source files and 1,506 proof-file hashes.
The verified v54 hosted planner and its previous results remain the baseline.

The source-only canonical reservation adapter reproduces the pinned original
`init.c` include/call transform, a fresh build identifier, and the exact original
reservation extension. It does not execute the older preparer or generate its
minimal-init/CPIO. Disabled preparation preserves this explicit reservation-only
source/config baseline byte-for-byte. Enabled preparation adds guarded includes
and a guarded call with a default-n `CONFIG_NOTE10_XNU_RUNTIME_PLAN` option.
The existing phone/PM build chain remains unchanged.

The source and host checks establish admission only after successful current-boot
reservation status, a base at least 2 GiB with 32 MiB alignment and a 40-bit bounded
256 MiB extent, and a full valid reserved-page count. The wrapper passes that
numeric base, hash-bound actual payload geometry and a tiny explicitly synthetic
ADT to `n10_rt_plan`, using local output. Its bounded `N10XRP1` diagnostic checks
metadata-prefix offsets, kernel/entry/end offsets, seven mapping blocks and two
kernel blocks, with `synthetic=1 materialized=0`. The wrapper never accesses the
reserved window or invokes serializers, metadata construction, MMIO, register,
PM or transfer operations. This describes the guarded implementation and host
evidence; neither actual kernel object was executed.

Actual dependency closures contain 730 files in disabled mode and 735 in enabled
mode. The pinned Linux type header already supplies the stdint aliases; no
conflicting duplicate typedefs were added. The enabled object's wrapper-to-planner
`R_AARCH64_CALL26` relocation binds the integration. Disabled object symbols,
marker and runtime dependencies are absent, and disabled preparation is identical
to the canonical reservation-only source baseline. The proof binds actual archive,
source/header, toolchain, configuration, command, `.cmd` and object bytes. These
checks make no claim that the entire Linux `init.o` lacks privileged operations
or mutable globals.

The focused checks passed 32 host-wrapper cases, three frame mutations, 17
preparer/manifest cases and 36 dependency cases. Corresponding saved local proofs
also passed. The host harness injects reservation state and a planner stub; it
checks wrapper guards, current-base propagation, failure reporting and plan-field
rejection without executing the production planner or a Linux object. Existing
v54 native/ABI/entry and PM suites were not replayed locally.

Failed [CI 41055821209](https://github.com/eirblue/ios_note10p/actions/runs/41055821209)
and [CI 41056966619](https://github.com/eirblue/ios_note10p/actions/runs/41056966619)
remain part of the history. The first exposed a dependency capture that omitted
the final continued line's newline and left a lone backslash. Continuations now
join before logical assignment parsing. The second exposed Kbuild's separate
`source_` assignment for the primary translation unit, which is absent from
`deps_`. Unique source/dependency/command assignments now bind the same object
and the exact primary source while retaining the required source/root gates.
Actual proof bytes are captured before later validation, and both modes compile
before dependency/object acceptance.

v55 produced no full Image, BOOT, minimal-init or CPIO and performed no device
operations or reserved-window materialization. It establishes neither physical
ownership, GIC handoff, DMA quiescence, XNU execution, iOS boot nor deployment
readiness. v54 and earlier physical-test history remain separate and preserved.
