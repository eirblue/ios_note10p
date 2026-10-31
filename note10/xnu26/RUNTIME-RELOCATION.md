# Runtime relocation metadata and PC data trials

## v59 production AArch64 PC execution passed

Tested source `5c3ca5f5a3b21af725701df16e057a485d9add76` passed
[CI 41167139172](https://github.com/eirblue/ios_note10p/actions/runs/41167139172),
attempt 1. The authenticated parent reader verified actual run/job/step success,
artifact API digest, every extracted member, exact source and upstream input
lineage, the final closed ELF and full saved observations. The v59 result SHA-256
is `8c11e9c3a2b27c06fd43afc2ceb4fe149aa861fea1bd818d32fd0f478f658113`.
This tested source is separate from the result-document publication commit.

The unchanged production planner and relocation-trial C/H are linked into a
statically closed AArch64 ET_EXEC with a read-only ABI oracle. No fixture
observer, runtime callback, writable global or external dependency is linked.
The actual target instructions execute in Unicorn 2.1.4 over PC-owned mappings;
the XNU payload is data in a non-executable buffer. Code is RX, oracle/input
pages are read-only, and stack/output pages are RW/NX. The numeric requested
physical base `0x80000000` is left unmapped and is distinct from buffer pointers.

All four target cases passed: real overlapping relocation and restoration;
a deliberately corrupted transient byte returning INVALID followed by complete
restoration and an unchanged result sentinel; insufficient backup capacity;
and overlapping window/backup rejection before writes. The latter two preserve
all caller outputs. The target-size probe yields request/result sizes 96/48
bytes. All twelve AAPCS64 arguments, sentinel return PC, 16-byte aligned SP,
x19-x29 and the low 64 bits of v8-v15 are checked independently of return counts.

Address-filtered memory watchers record the real target bytes before the single
mismatch injection and again before restoration, together with the complete
backup and before/after buffers. Deterministic compressed, deduplicated full
observations are bounded-decoded by the parent reader and compared byte for
byte. The exact 19,578,880-byte payload moves to offset `0x1004000`; the entire
36,372,480-byte affected prefix (`0x22b0000`) and sentinel guards are restored.
Observed PCs bind the backward store, comparison read and restoration store to
the retained production ELF/disassembly. No per-instruction observer replaces
the copy or comparison code.

Eight wheel-metadata fixtures and six instruction-binding fixtures also pass.
The metadata parser accepts LF/CRLF headers and rejects wrong, missing or
duplicate identity/version headers. Byte-store binding accepts only STRB/STURB
at the checked function extents and rejects wider stores or misplaced PCs.
[Arm's instruction reference](https://documentation-service.arm.com/static/6245c734b059dc5ff9a8bdab)
defines STURB as the unscaled byte-store form. The earlier
[CI 41166367312](https://github.com/eirblue/ios_note10p/actions/runs/41166367312)
remains failed: all four model subprocesses completed, but the final binding
checker rejected the actual Clang14 STURB. A retained-data postcheck verified
the narrow correction without replaying that emulator or changing its CI status;
the successful corrected run above is fresh.

The configured per-case ceiling is two billion instructions, with 180 seconds
of emulator timeout and 210 seconds of process timeout. These are bounds;
no executed instruction count is claimed. FP/AdvSIMD access is explicitly
enabled only in the model. This does not prove physical EL1/FPU readiness,
reserved-RAM ownership, asynchronous-PM ordering or init-memory lifetime.
No device, BOOT or Linux Image action occurs in v59; v57 remains the last
physical result with its single cycle consumed. No hardware XNU execution or
iOS boot is established. Passed unchanged historical suites were not replayed
locally; the preserved v58 hosted evidence and this target execution are distinct.

## v58 overlapping payload trial passed

Tested source `12549ffe88438aa583690da744b9a8d035d84019` passed
[CI 41161078327](https://github.com/eirblue/ios_note10p/actions/runs/41161078327),
attempt 1. The actual parent-pinned reader verified the authentic run, job and
required step successes, artifact API digest/member bytes, exact source/input
lineage, closed production object and independent saved byte comparisons.
The saved v58 result SHA-256 is
`5ada19a339fce7b56209bc31e1aa3fad998bea66cd34c73ad427c88924619f7d`.
The tested source is distinct from publication of this result documentation.

The new separate `runtime_relocation_trial.c/h` adds a data-only rehearsal over
caller-owned PC buffers. The existing v54 planner/serializer sources remain
byte-identical. The planner is recomputed from the request; numeric physical
addresses supply offsets only and are never converted into host pointers.
For the verified flat payload, 19,578,880 bytes move from window offset0 to
`0x1004000`. These spans overlap, so the actual path copies backward. A separate
backup saves the entire affected prefix `[0, 0x22b0000)`, or 36,372,480 bytes,
before any window write.

Capacity, pointer-overflow, alias and request admission precede output writes.
A pre-admission rejection preserves window, backup and result. After admission,
backup is output scratch holding the original full prefix; its old contents
are not promised on an admitted failure. Every post-write path restores the
whole affected prefix and compares it. The result is committed only after
successful transient verification and complete restoration; failures leave the
result sentinel unchanged. There is no new metadata, adapter placement or
execution transfer in this trial.

All 48 new host-native cases passed, including the real overlapping move,
boundaries/admission rejections and an injected transient mismatch. The fixture
captures actual destination bytes before comparison/restoration and before its
optional mismatch injection. Independent pre-call and transient snapshots,
separate from the algorithm's backup, prove payload identity and complete-prefix
restoration for both the successful and injected-failure cases. These 48 cases
are a new trial matrix, distinct from the preserved v54 metadata matrix below.
The 39 instruction-classifier fixtures also passed. Existing entry/VM/seed
models and earlier unchanged native suites were not replayed locally.

The hosted fixture is deliberately instrumented; an additional uninstrumented
freestanding AArch64 trial object has only the intended planner dependency.
Linking it with the pinned planner yields a closed object with no unresolved
symbols or writable global state. Decoded instruction fields pass the finite
ordinary-operation policy and reject unknown/system/explicit trap instructions.
The AArch64 object was not executed. SIMD access depends on processor control
state, so this code-generation audit does not establish FP setup or kernel/EL1
execution readiness. [Arm's A64 reference](https://documentation-service.arm.com/static/6245c734b059dc5ff9a8bdab)
describes the conditional trapping behavior of these SIMD operations.

The upstream source artifact is bound to native run39560904016, attempt2,
its exact source head, archive digest and the Mach-O/flat-payload hashes retained
below. A prior [CI 41160322285](https://github.com/eirblue/ios_note10p/actions/runs/41160322285)
remains failed: Clang14 produced five ordinary data-operation mnemonics missing
from the initial finite classifier. The correction added only those observed
operations and focused cases; the transaction C core, harness and pinned
planner were unchanged. The accepted fresh CI compiled and tested the corrected
canonical source rather than promoting the failed run.

v58 performed zero phone operations and built no BOOT or Linux Image. It did
not relocate an image in physical reserved RAM or establish ownership, DMA/GIC
handoff, XNU execution or iOS boot. Late-init/async-PM ordering and init-memory
lifetime remain separate requirements for any future physical integration.
The v57 physical result and its consumed single cycle remain unchanged.

## v54 preserved native metadata component (PC only)


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
