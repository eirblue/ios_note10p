# v54 native runtime relocation component (PC only)

This component prepares a synthetic relocation using reusable freestanding C and has passed the focused PC checks reported below. It does not reserve RAM, write physical metadata, change Linux or phone boot images, or authorize an XNU transfer. The v53 physical result and all earlier records remain separate and unchanged.

`runtime_relocation.c` contains the planner, canonical bounded ADT validation, 1152-byte boot_args v2 serializer and original 64-byte `N10XFER1` serializer. It has no I/O, heap allocation, mutable globals, MMIO or assembly. The host harness supplies its own file I/O. Caller inputs must identify valid readable buffers; output buffers must be writable and disjoint. Rejection preserves all output bytes. Physical range arithmetic, 40-bit limits, alignments, occupied/reserved conflicts and initial mapping coverage are checked before output publication.

For the reviewed native XNU image, the planner derives the virtual RAM base by rounding its actual image VA down to a 32 MiB boundary. The physical base `B` is a caller-supplied synthetic parameter, never a measured phone address or an inferred free-memory region.

| Item | Derived geometry |
| --- | --- |
| Virtual RAM base | `0xfffffff006000000` |
| Modeled RAM | `B` through `B + 0x10000000` (256 MiB) |
| Physical base bounds/alignment | At least `0x80000000` (2 GiB), 32 MiB aligned; modeled extent below `2^40` |
| Kernel start | `B + 0x1004000` |
| XNU entry | `B + 0x1340490` |
| Kernel end / topOfKernelData | `B + 0x22b0000` |
| Arguments / synthetic ADT / adapter pages | `B`, `B + 0x4000`, `B + 0x8000` |
| Initial mapping | Seven 32 MiB blocks; kernel spans two blocks |

The input Mach-O SHA-256 is `b2c80dea6762dc8a388563a099810b48a9157533c6b9c9db8889c29bdddf8d3f`; its materialized kernel.mem SHA-256 is `7a573eb6d2f5efc87bd5c85af130ea854eb4bad8370d17a4247e54f9593a836a`. Existing strict artifact parsing binds segments, entry and actual bytes. These hashes identify source-built research inputs and confer no physical ownership.

The ADT is an explicit parser fixture, bounded to one metadata page. The C validator accepts a deliberately limited canonical subset (32 nodes, 32 properties/children per node, depth at most eight), checks names, duplicates, padding and complete consumption, and rejects a `gic-handoff` node or property. The independent existing ADT codec also checks the fixture. There is no live Linux-DT conversion or GIC ownership declaration. The command-line producer accepts at most 1023 printable ASCII bytes without NUL.

C-produced boot_args bytes are padded to a page and used directly. C-produced transfer-record bytes patch the actual adapter's existing record slot directly; flags, reserved fields and status remain zero. Python independently verifies the resulting four-buffer manifest through the existing codecs and bundle loader. It does not use the old Python `construct` producer to replace the C metadata.

`runtime_relocation_abi.json` contains only the saved real-header oracle's 13 numeric offsets, structure size, header digest and public source commit. The new proof builder compares fresh ARM64 own-layout object data, all 1152 C serializer bytes and the independent Python codec. When supplied locally, the preserved real-header object and copy-provenance record are read and checked without recompiling that old oracle. A separate fresh AArch64 object checks freestanding code generation, unresolved dependencies, writable globals and privileged instructions; it is not executed.

The targeted workflow passed the native boundary/mutation/canary checks and exactly one new actual-XNU/actual-adapter instruction case using the C-produced bundle and explicit C-derived virtual RAM base. The shared entry helper retains its original default and all RAM, fetch, segment, DAIF and pre-MMU checks. Old entry, VM, seed, PM and historical suites were not replayed. Test output stays inside the project's private workspace and disjoint from input artifacts.

Any later phone relocation would overwrite the old kernel-at-base data-only checkpoint. It requires new phase-specific evidence, new hashes, final gap/tail checks and separate authorization. The old `N10XNU1` data-stage result cannot certify a final handoff layout. Full DMA shutdown, physical ownership, phone XNU execution and iOS boot remain unverified by this PC component.

## v54 verified PC result

Source commit `78797cb2e37e97d99463217f5418740a5ed76141` passed [CI run 41050904567](https://github.com/eirblue/ios_note10p/actions/runs/41050904567), attempt 1. Review bound the actual artifact and its 13 source digests to that source. The result passed 48 native cases and six bundle mutation rejections. C-produced arguments and record bytes formed the four-buffer bundle directly, retaining the reviewed actual Mach-O and materialized kernel digests above.

The successful CI result contains exactly one new actual-XNU/actual-adapter instruction-model case. It executed 24,839 instructions, stopped before the MMU-enable write and retained modeled DAIF `0x3c0`. All existing RAM, fetch, segment-endpoint and boundary checks remained active. This is execution inside a synthetic PC instruction model; no phone operations or phone XNU execution occurred.

The ABI comparison covered all 13 offsets and all 1152 serialized bytes against fresh ARM64 own-layout object data and the independent codec. A separate successful local operator proof also compared the preserved real-header oracle object without recompiling it. Fresh freestanding code-generation checks found no unresolved dependencies, writable globals or privileged instructions. The CI object decoded 1,355 instructions; the local object decoded 1,215 with a different compiler. Those counts describe separate compiled objects, not the 24,839-instruction XNU/adapter model case.

Earlier [CI run 41050510506](https://github.com/eirblue/ios_note10p/actions/runs/41050510506) remains failed. Its final dependency gate compared Capstone's module-reported `5.0.7` with the pinned distribution `5.0.9`. The correction checks installed distribution metadata before native or model work and keeps module versions as separate diagnostics. The distribution pins remain Unicorn `2.1.4` and Capstone `5.0.9`.

The result certifies the bounded PC component and its source-bound synthetic bundle. It does not establish physical RAM ownership, GIC handoff, full DMA shutdown, phone XNU execution or iOS boot, and does not authorize device integration.
