# Runtime relocation metadata and PC data trials

## v74 real-input stop and v75 bounded-property scan design

Source `7c652372d2acbc4b5995f146d520fa73fd252d60` passed 34 new synthetic methods once in [CI 41319014723](https://github.com/eirblue/ios_note10p/actions/runs/41319014723). The first preserved-input conversion exited 1 at the combined duplicate/property-count guard, producing neither fragment nor manifest. The input and failure remain preserved; the unchanged converter was not retried.

A data-only inventory distinguished an artificial 128-property ceiling on unrelated nodes from an actual duplicate. The v75 design retains the 128-property budget for /cpus and its direct children and rejects duplicate names throughout the tree, while bounding the other property scan by the existing input size and minimum property-header size. Only new directly affected cases are selected; the passed 34 methods are not replayed.

This is PC-only incomplete CPU-description conversion, with no new Image or device action and no replay of the consumed v73 cycle. The nearby XNU reference is not an exact target ABI. CPU execution state, platform compatibility, complete boot-tree readiness and XNU execution are not established. Raw data and live-derived fragments stay private.

## v73 SHA256 incremental input and same-transform state-copy result

Source `7e4a8c992f95f01429e824404378fa9271c0eb8e` passed [CI 41312767945](https://github.com/eirblue/ios_note10p/actions/runs/41312767945). The new Linux diagnostic uses six patterned messages of 55, 56, 63, 64, 65 and 129 bytes. Each checks incremental update/final and export/import into a distinct descriptor on the same transform. Descriptor/state allocations are bounded and no opaque state bytes are logged. This is not a portable state ABI or an XNU execution result.

Twelve new host methods passed once, including one new native fixture compile and five scenarios. These are not 17 independent methods. The old abc KAT and passed historical suites were not replayed. Successful CI proceeded directly to necessary packaging and one physical cycle; no separate post-build reader or second source review ran.

The actual device capture passed the six new cases and minimal PID1 observation. It retained 16 arm and 16 recovery-request frames; the host observed a changed boot ID and the same bound root TWRP. One BOOT write and one host reboot attempt consumed the v73 cycle, which must not be replayed. Seventy of 71 recovery polling observations reported transport errors before normal recovery appeared; hardware boot events were not independently counted. The log decoder's static hardware-reentry=false is kept separate from the host observation.

The installer's pre/post five-partition checks completed without mismatch, but individual node/hash rows were not persisted. No duplicate follow-up device reads were added. XNU execution, physical ownership transfer and iOS boot remain outside this result.


## v72 builtin minimal Linux PID1 and SHA256 physical result

Source `149cb74c3f7640f2e26dfdcd1d775ec99f6c02ac` passed [CI 41307031423](https://github.com/eirblue/ios_note10p/actions/runs/41307031423). Its 46,413,836-byte Image has SHA-256 `fa655a1aeca9e6c8820d91e1f53d7f64f321a0f8a930c4d5a879a8582cd3de69`. A forced builtin minimal `/init`, a default-off guarded route, and `rdinit=/init` with CMDLINE_EXTEND prevent the diagnostic from falling back to Android block-root while retaining bounded bootloader argument append.

One BOOT write and one host reboot attempt completed. The strict device capture passed the minimal PID1-start and SHA256 diagnostic, with 16 arm and 16 recovery-request frames. The host observed a changed boot ID in the same bound root TWRP; pre/post five-partition checks completed without mismatch. The single allowed v72 cycle is consumed and must not be replayed.

Recovery polling included repeated sideload-not-shell errors before a later normal recovery transport. Hardware boot events were not independently counted. The decoder's constant hardware-reentry=false states that log frames alone cannot prove hardware reentry; it is separate from the host's observed recovery. No exact clean boot count, XNU execution, or iOS boot is claimed.

The 37 new tests passed once under the original source. Header and configuration dependency corrections used build-only continuations, without replaying those tests. Per the user's latest workflow, successful CI proceeded directly to necessary packaging and the device test; no separate post-build Image reader ran. Unnecessary repeated verification is omitted throughout subsequent cycles, while fresh installation safety checks and the per-build single-use limit remain.


## v71 diagnostic Image passed; device attempt failed with four reported boots

Source `9bfe108e7fd7a063bacce9418be46d269cb872d9` passed [CI 41290669542](https://github.com/eirblue/ios_note10p/actions/runs/41290669542), attempt 1. The first actual Image target produced 46,348,300 bytes, SHA-256 `2d8c7f82a939817e73c7dfb059b36e198eb3b441f5d0f69ee5e4220d239821eb`. The compiled code keeps the KAT callback outside freed init memory and queues it separately after the existing recovery arm and `SYSTEM_RUNNING`; the physical boot route remains unverified.

The earlier [CI 41288159718](https://github.com/eirblue/ios_note10p/actions/runs/41288159718) failed configuration validation before any Image target. Its four worker integration methods, including 11 C-stub scenarios, passed once and were carried without replay. The corrected CI's four new configuration-policy methods and the separate 13 host-profile methods each passed once. Host source `5e233aa5f08473d716ca2e9b3d8937c1821d513f` is distinct from the Image-producing commit.

The host issued one BOOT write and one reboot-command attempt, consuming the build's single authorized cycle. The user reported four observed boots: three carrier-logo appearances before 90 seconds and a final TWRP screen. Carrier logos do not prove completed Android boot; the intended diagnostic TWRP/external-ramdisk route and the repeated boot sequence require diagnosis. The original run failed after 240 seconds without verifying a changed boot ID. Later read-only observation verified the same bound device in normal root TWRP 3.7.0_9-1 and all five partition integrity checks. The pre-reboot ID was not persisted, so automatic recovery, an ID change and return within the deadline remain unproved. No additional host flash/reboot command was issued; the failed journal is unchanged and v71 will not be replayed.

A subsequent raw capture was preserved unchanged but rejected by the strict profile: it lacks the zero-time, self-contained boot boundary, and the full producer banner occurs only in panic context. It reports a fatal-exception panic in the bootchecker context at about 54 seconds, before the existing nominal 90-second recovery-request delay. This observation does not establish root cause. Candidate KAT/arm entries were not accepted as runtime proof, and no request-phase evidence was accepted. No frame repair, log merging or acceptance bypass was used.

No accepted KAT/provider or automatic-return proof, XNU/iOS execution or deployment readiness is established. Synchronous crypto has no hard cancellation guarantee; frame checksums do not authenticate a boot.

## v70 default-off SHA256 runtime observation component (PC only)

Source `8d569c4c7c69c14c26f7c0b41040c5f15a783d65` passed [CI 41284756768](https://github.com/eirblue/ios_note10p/actions/runs/41284756768), attempt 1 (workflow 403362451, job 124783698203, artifact 13073739663). The parent strict reader completed with observed exit code zero; result SHA-256 `eeefdc07b7af17273982cb1e8999697f290251859dcca14b51067972bcb37d04`.

The default-off late-init SHA256(abc) observation component compiles against the pinned kernel headers and effective configuration. It checks the exact requested/returned `sha256-generic` driver, bounds descriptor allocation to 4,096 bytes, cleans up resources and emits two build-ID/checksummed frames for strict decoding. After standard Kbuild preparation, the sole new kernel target was `drivers/misc/note10_sha256_kat.o`: an 18,056-byte AArch64 ET_REL object, SHA-256 `456c1ce5e0dec89ef005954d745c353b4617446995193d47f73dc2ff198a93d9`. Build evidence ID: `e96961c529993911f0152475acbd8ba9`.

Six new unittest methods passed once in that same CI, including ten canonical-C stub scenarios for success, rejection, callback failure, descriptor boundaries and resource cleanup. The native fixture compiled once before the new kernel object build. These are six methods containing ten stub scenarios, not 16 independent tests. No local rerun or replay of passed unchanged tests occurred. Only host stubs ran; neither the real kernel object nor the actual crypto provider was executed.

The canonical ZIP is 755,731 bytes, SHA-256 `926c69a3c0886d12d00a7ab2b4808d5657075637b3e3a96bbe300458cc82603c`; all 515 members and 2,325,852 expanded bytes are bound. The reader bound 11 source records (seven new and four inherited), 438 actual compiler prerequisite file hashes and 16 recorded commands. Its fresh authenticated metadata/log reads reused the canonical collection without another ZIP download or extraction.

This is a compile/control-flow prerequisite, with no true kernel SHA256 result, runtime provider availability, recovery integration, Image/BOOT, XNU/iOS execution or device readiness claim. Synchronous crypto allocation/digest have no established hard cancellation or local time bound; frame checksums detect damage and do not authenticate a boot. Device/BOOT/reboot operations are zero; device authorization and deployment readiness remain false.

## v69 finite parser-observed cra_u body relation

Source `693ebea876130431f90f1632f4183a6bc0494f95` passed [CI 41280546185](https://github.com/eirblue/ios_note10p/actions/runs/41280546185), attempt 1 (workflow 403333091, job 124771405231, artifact 13073400790). The parent reader completed with observed exit code zero. Its result SHA-256 is `b6be4d340ecaccb244f918b7a1cc09d74a67b21f11cdb354995d6347b4e882d5`.

The new finite relation covers only 78 newly reported provider/core union-body nodes, 39 per role: 54 members, eight structures and 16 pointer records. Each union has four direct members. Closure binds 54 child edges, 16 inherited contexts and 16 opaque pointer contexts; the reader recomputed 39 paired comparisons, with zero unsupported or unresolved records. The exact accepted v68 scalar pair is a premise, without re-extracting its type graph. Disjointness from the old 210 IDs remains an accepted raw-query label, not a new measurement. The sole raw query is consumed; actual CI and reader perform byte/slice binding and the new data relation, with no ELF/DWARF query or old proof replay.

The canonical ZIP is 5,042,425 bytes, SHA-256 `3d1ac0ecb90fe875ec044a559358dd6b63231b3499c1b0dcfc6f2f8a64b57869`; its complete 28-member map contains 5,758,074 expanded bytes. Source-first gates cover seven public blobs in CI and 11 local source records. Producer and stager perform eight bounded read-only local Git source-provenance reads each. The fresh collector performs six authenticated requests including one ZIP download/extraction; the root reader independently refreshes four current metadata endpoints and its exact job plaintext log, with no ZIP GET or extraction. Current private log validation accepts only bounded exact SGR tokens while preserving original raw bytes and digests; identity comes from authenticated API tuples and required steps, not log captions. The successful CI and public sources were not rerun or changed for that private adaptation.

Public 24 cases passed once under CP1, private eight under CP2, and the three new SGR cases under CP3; the schema audit passed once under CP1. These are source-attributed histories, not a combined CP3 rerun of all 35 cases. The earlier zero-completed Windows mock failure, strict-log failure before ZIP retrieval and zero-case preimport review-key failure remain preserved. No completed case, schema audit or query was replayed.

This parser-observation-level relation supplies no independent lexical DIE-boundary certificate, pointer width, pointee or signature equivalence, alignment, member storage extent, whole ABI or runtime guarantee. It does not establish Image/BOOT integration, XNU/iOS execution or device readiness. Device/BOOT/reboot operations are zero; device authorization and deployment readiness remain false.

## v68 verified reported provider/core metadata relation

Source `a8f44533e1253344dfa12d9bad4326306262f2c0` passed [CI 41270579838](https://github.com/eirblue/ios_note10p/actions/runs/41270579838), attempt 1: workflow `403262274`, job `124742348929`, artifact `13068584319`. Independent actual-result review accepted only the finite reported metadata relation. The parent strict reader ran once with observed exit code zero and all 70 recorded guards stable. Accepted result digest: `73379d106ca76515330e33ab21b2213b1dfaca0484f38d3321d76ea252d3eefc`.

The relation covers the reported direct `shash_alg` and embedded `crypto_alg` member/type metadata and the emitted `crypto_register_shashes` prototype records in the uniquely selected provider and core compilation units. The two roles together contain six candidates, 210 graph nodes, four expanded aggregate records and 56 direct member records. Both reported `shash_alg` sizes are 768 bytes; both `crypto_alg` sizes are 512 bytes with explicit alignment 128. Exact embedded-base identity, reported member starts/order/names/explicit alignments, qualifier placement and positional prototype type references are compared. The provider declaration marker and the core subprogram record remain distinct; this is not machine-code ownership or calling-convention evidence.

Sixteen other aggregate records remain opaque, with 24 recorded contexts stopping at their reported tag/name/size/alignment metadata. Their internal members and transitive layouts are unmeasured, including opaque by-value dependencies. All 42 pointer records omit explicit byte size; `shash_alg` also omits its own alignment. Common CU address-size metadata does not supply a measured pointer width, complete member storage extent or missing structure alignment. Matching absent return/pointee/type attributes do not invent additional type records or prove pointed-to layouts.

One earlier private raw DWARF observation supplied the independently reviewed finite profile and is permanently consumed. The actual CI and parent reader performed no ELF/DWARF parsing or query, no old proof/helper replay and no compiler/linker/make work. They recomputed only the new finite relation from the fixed accepted profile, binding the unchanged accepted object and four raw debug-source slices by complete bytes/SHA. No raw query report, source audit, private path or raw job log is published here.

The current complete ZIP is 2,414,430 bytes, SHA-256 `488b929289609790f103ca46e7360f6dd8db23735f148f17e820e1a693372ea7`; all 28 ordinary members and 3,250,425 expanded bytes are bound to the canonical collection/extraction maps. Seven published source/control blobs, 11 local source records, authenticated current run/head/attempt/workflow/job/required-step/artifact/plaintext-log evidence and the separate accepted input/private-result identities are bound. The strict-reader result digest is `d3d3c93effdddbd7bb5917679e3d1330a02452095f13ae4eb8b637f55b341eb8`.

The 32 new public and 11 new private cases passed once, and the actual fixed-control schema preflight passed once. Completed prior cases, queries, proofs and audits were not replayed; actual CI invoked zero fixtures. The first collector failed on a private pin-shape mismatch before any API or ZIP request and remains preserved and unaccepted. A metadata-only pin correction enabled the one successful collection, one current ZIP download/extraction and one strict-reader invocation without source changes or CI retry. The retention plan found zero eligible items and deleted zero items.

This result does not prove transitive opaque layout equivalence, complete member storage extents, pointed-to layouts, whole binary ABI or toolchain identity, runtime provider/service availability, allocation, registration or callback execution, Image/BOOT integration, XNU/iOS execution or deployment readiness. Device, BOOT-write and reboot operations are zero.

## v67 verified provider/core relocatable pair origin

Source `d5a1c2eb98d7a102f5b5b7b86dd9b1eea68cd943` passed [CI 41261305654](https://github.com/eirblue/ios_note10p/actions/runs/41261305654), attempt 1. The parent strict reader ran once with observed exit code zero and independent actual-result review accepted the finite result. Result digest: `1a34e40b7d08a2bc1c9a09f111540b3c80463933f19658321655250597835950`.

The unchanged accepted provider and core objects were linked in that order with the pinned GNU ld 2.38 role, using `-m aarch64linux --no-relax -r`. Exactly one version invocation and one target link ran; neither object was recompiled. The new `provider-core-pair.o` is 689,704 bytes, SHA-256 `e60e831e681e51e9d676ccf437255f92273773c1fad3d80251018ec8097a8832`. The exact contextual provider GLOBAL/NOTYPE undefined registration reference becomes a unique core-owned GLOBAL/FUNC definition. This is a relocation/definition fact, not registration execution or a general symbol-type relaxation.

The finite proof preserves ten uniquely owned full spans and all 13 typed RELA records in three selected sections: provider init (3), passive algorithm table (8), and core registration target (2). Only observed ABS64, ADR_PREL_PG_HI21, ADD_ABS_LO12_NC and CALL26 forms are allowed, with per-row destination/coordinate checks and only enumerated section-symbol rebasing. Seven direct-only spans are byte/definition-origin witnesses; their complete outgoing relocation sets and execution semantics are not proved. The 21 unrelated same-name input section groups are outside this projection. Frozen accepted input labels and exact whole-object/slice bytes are consumed as data; the producer and parent parse only the new output, with no input ELF, old semantic, CFG, DWARF, origin-model or query replay.

The complete current ZIP is 1,113,533 bytes, SHA-256 `83829d08a8227b4a2c0361ff68a2009a1daf6168ec286ed04fbbdbfc266d3bf8`; all 37 ordinary members and 4,543,297 expanded bytes match the canonical collector and extraction maps. Authenticated current run/job/five required steps/artifact/plaintext-log records, the fixed control, 12 local sources, eight exact published/source-archive blobs and the separate accepted v66/private query identities are bound to separate collection and reader pins. The original complete v66 input ZIP is retained unchanged; no selected-object repack substitutes for it. The current artifact was downloaded and successfully extracted once.

Historical checks retain their original source attribution: CP1 public 34/private 8 cases and one actual-control schema audit; CP2 changes only workflow scratch-parent preparation; CP3 adds five private log-gate cases. The collector's valid BOM-prefixed UTF-8 runner log is authenticated through the exact current API/job/step tuple rather than requiring human step captions inside the log body. That private transport correction changes no published producer or linked output and triggers no new CI/link. The first CI failed before version/link execution and remains unaccepted. The first collector stopped before any ZIP GET and remains unaccepted. Completed cases, query and schema audit were not replayed; these histories are not a combined current-source regression claim.

Raw output observations include 369 section headers, 577 symbols and 12,574 relocation records; the semantic claim remains limited to the 13 selected relocation records and ten spans above. There are 27 raw undefined records including the null entry, leaving 26 named external symbols. Binary ABI, independently measured core or paired layouts, whole toolchain identity, runtime compatibility, provider availability, allocation success, registration/callback execution, full Image/BOOT, XNU execution, iOS boot and deployment readiness remain unproved. Device/BOOT/reboot operations are zero; the consumed v57 cycle remains 1/1 with no journal replay.

## v66 verified provider/core declared interface and metadata edge

Source `2697cb0d48b42c9e0ab5d01509ada82e5c0d94f7` passed [CI 41254506469](https://github.com/eirblue/ios_note10p/actions/runs/41254506469), attempt 1. The parent strict reader ran once with an observed final exit code of zero; independent result review accepted the bounded result. Result digest: `bd76c1601856844cb5cdb287b75b0287ef7234e19b7bba501c7e63793f11823e`.

This data-only result joins the accepted v63 provider's `sha256_generic_mod_init` CALL26 reference to the accepted v65 `crypto_register_shashes` definition. The undefined provider GLOBAL/NOTYPE symbol and defined core GLOBAL/FUNC symbol are bound as one exact contextual pair; no general symbol-type relaxation follows. New raw table relocation coordinates bind eight callback entries to the original accepted provider definitions. No callback was executed.

The declared input profile binds the exact `int crypto_register_shashes(struct shash_alg *algs, int count);` prototype, 351 common source/include headers, and three generated configuration files whose only differences are the frozen LOCALVERSION physical lines. Provider/core complete header sets remain distinct. Saved compiler arguments each contain 89 tokens, with 84 identical tokens and three exact role-specific blocks. Retained Clang/resource and other recorded tool observations are checked; unavailable v65 external GCC and both external assembler identities remain explicit gaps. Provider layout labels belong only to original v63 evidence: they are not an independently measured v65 layout, paired DIE equivalence, emitted binary ABI, whole-toolchain or runtime compatibility proof.

The complete current ZIP is 289,046 bytes, SHA-256 `7f4322654a01fb1c9d75a45557e2569636fcead7e3c5a19b11e784bc89a061ce`; all 33 ordinary members and 1,023,685 expanded bytes match the canonical extraction map. Authenticated current run/job/three required steps/artifact/plaintext-log records, 12 local sources, eight exact published blobs and both immutable accepted original ZIP/private-result identities are bound to fresh collection and separate reader pins. Each original extraction is checked against the same complete authenticated original ZIP inventory before producer labels are parsed; the provider-only `independent-verification.json` is opaque bytes, with no invented direct control-member digest or semantic interpretation.

Fixture history remains attributed to original checkpoints: CP2 public 42/private 12 passed outputs, CP3 three new cases and a separate schema audit, CP4 ten new cases and a separate namespace audit. The CP2 private process-wrapper metadata was lost: observed exit code remains null despite the historical reported zero. CP4-R2 changes only the fixture's final CRLF to LF; no fixture or audit was rerun under that revision. These are not a combined current-source regression pass. The two earlier actual CI failures remain permanently unaccepted. No prior semantic checker, compiler, linker, model or probe was replayed.

The two objects have not been linked together. Registration, allocation success, runtime provider availability, callback execution, full Image/BOOT, XNU execution, iOS boot and deployment readiness remain unproved. Device/BOOT/reboot operations are zero; the consumed v57 cycle remains 1/1 with no journal replay.

## v65 verified crypto hash composite origin

Source `8d9678bcc0fb4046093e637ed8d8c61d523b79f2` passed [CI 41242201836](https://github.com/eirblue/ios_note10p/actions/runs/41242201836), attempt 1. The root strict reader ran once and exited 0; independent actual-result review accepted the static PC-only scope. Immutable private result digest: `174deddddbd6de3d3e0f8fb12384053bdcd7d197b536bede2254cb071d99c233`.

The stock Kbuild target `crypto/crypto_hash.o` links `ahash.o` then `shash.o` through the pinned GNU LD-r branch. Composite SHA-256: `485b20e7075dc356325a0d33049b664ef7cc9f3c11a29838c0fc5221267b4edf`. The finite mapless proof binds 11 selected shash identities (ten functions and the passive `crypto_shash_type` table), 21 owned sections, complete selected bytes, symbol metadata and typed RELA records. It preserves the accepted v64 selected byte/relocation identities without rerunning its instruction, DWARF, callback or CFG proofs. This does not assert whole-object byte equality with v64.

The complete 702-entry shash prerequisite map, three generated configuration files and normalized CC arguments equal the accepted v64 inputs. Mandatory primary C source capture is bound to its saved source assignment, single CC source operand and declared leaf mapping; bounded stable reads retain one buffer for copied bytes and SHA. The actual GNU make trace includes expanded leaf postprocessing and composite recipes; conditional branch execution remains unobserved.

The original ZIP is 2,836,090 bytes, SHA-256 `8a81d7add74142ff009ae72a7bb9c09f7af2fb5fd76da445a8218acaf35fdf4e`; all 1,454 ordinary members and 9,543,577 expanded bytes were checked against the canonical collection map. The run/job/five required steps, individual artifact, current authenticated plaintext log, 16 local sources, 12 published blobs and both protected complete kernel/v64 ZIP inputs are bound to the fresh collector and separate reader pins. No selected-object repack replaced either original artifact.

Fixture history remains tied to each original source checkpoint: CP1 public 120/private 42, CP2 53, CP3 58, CP4 16, CP5 89; unpublished CP6 R1/R3 partial completion of five/23 cases and final R4's 33 new cases retain separate records. Completed cases were not replayed and final CI invoked zero fixture suites. These counts are not a combined current-source regression claim. Five earlier v65 CI failures remain permanently unaccepted.

Twenty-five external symbols remain unresolved. This result proves no ahash semantics, runtime provider availability, allocation success, callback execution, whole stack bound, full Image/BOOT build, XNU execution or iOS boot. Device/BOOT/reboot operations are zero; deployment readiness remains false. The consumed v57 physical cycle is not replayed.

## v64 verified shash core object static result

Source `31ece2db6e6b5391283db5bbc8e91f90af12ec52` passed [CI 41219611380](https://github.com/eirblue/ios_note10p/actions/runs/41219611380), attempt 1. The parent independently verified authenticated run/job/required-step/artifact records, the complete 3,134,662-byte ZIP (SHA-256 `58ce98c1b25e4a439fb2cc4cd0c5512c51bea2d4d6f6dd80fc3167abd72d6c90`), all 1,470 members (10,036,869 expanded bytes), the 34-file source closure and protected complete kernel archive. Full ZIP hashing and source binding preceded final candidate/pins. Parent result digest: `8245e788969baca254b1007fce93a428429bb7017e22c44a931ad7167e08d0d3`.

Actual Kbuild compiled stock `crypto/shash.o` and a separate data-only actual-header layout oracle. Mandatory DWARF and compiled-header facts bind the type table, descriptor-size bridge, registration/count/rollback CFG and preparation CFG. The 10 essential emitted functions contain 255 owned words: 251 ordinary GPR words and exactly four typed BLR sites with one-to-one callback/descriptor coverage. No arbitrary indirect-call or FP permission follows. Preparation binds three size-failure paths and 16 callback-presence paths, including the grouped export/import/statesize policy and branch-local zero return. The raw const-qualified `cra_type` target remains unchanged; its referenced complete `crypto_type` DIE is linked to the canonical actual layout digest rather than a handwritten size.

Scoped compiler frames total 400 bytes; this sum is not a whole-path or IRQ/OS stack bound. Descriptor allocation, external crypto/memory providers, runtime registration/init order, pointer/count validity and overflow safety, provider availability and physical safety remain unproven. These explicit-analysis objects are not a linked production Image. No provider, callback or oracle was executed; full link/Image/BOOT/device/reboot operations are zero. v57 remains consumed 1/1 with no journal replay; XNU execution, iOS boot and deployment readiness are not established.

Local CP1/CP2/CP3/CP4/CP5/CP6/CP7/CP8 results retain their original checkpoint labels and counts 49/28/14/76/53/50/165/86. Completed tests were not replayed, and these separate historical proofs are not a combined current-source regression pass. The final CI invoked zero fixture commands. Failed runs 41203755530, 41205176235, 41210655628, 41214486419 and 41217639368 remain failed and unaccepted with their raw evidence preserved.

## v63 verified SHA-256 provider object static result

Source `fc15da51e2295022796eb44779a1eb8008450b65` passed [CI 41199181822](https://github.com/eirblue/ios_note10p/actions/runs/41199181822), attempt 1. The parent independently bound authenticated run/job/step/artifact records, the complete 2,615,308-byte ZIP (SHA-256 `d8108f02426702d97bce53f5ae4f9c4bd7e318ec3476da0d17a477a57d1ea1c1`), all 1,216 members (8,286,855 expanded bytes), source closure and the protected complete kernel archive. Parent result digest: `76a4dd0a726db14c142c4d95611ac0cedb29646db6b02d6f41ab8b7063961db1`.

Real Kbuild compiled the stock `crypto/sha256_generic.o` and a separate data-only oracle using actual defining headers in the same source/config/compiler environment. Mandatory provider DWARF retains type sizes, member offsets and type graphs; only absent alignments come from compiled `sizeof`/`__alignof__`/`offsetof` expressions, with available DWARF facts crosschecked. No handwritten ABI fallback was used. `shash_alg` is 768 bytes/alignment 128, `crypto_alg` 512/128, `shash_desc` 128/128 and `sha256_state` 104/8 for this analysis configuration. The flexible descriptor context remains a flexible member at offset 128, without an invented size.

The mutable 1,536-byte registration array contains SHA-256/SHA-224 entries with 104-byte descriptor contexts, 64-byte blocks and digest lengths 32/28. Actual callback relocations and the initcall bind the array and count 2 to `crypto_register_shashes`. Nine scoped emitted functions contain 1,753 decoded GPR instructions; their compiler-frame sum is 576 bytes, with `sha256_transform` at 304 bytes. This sum is not a call-path bound. External `crypto_register_shashes`, `crypto_unregister_shashes`, `memcpy`, `memset` and `memzero_explicit` remain unresolved in this object. No whole-kernel/IRQ stack, runtime registration/init order, provider availability or physical safety is proven. The objects use explicit analysis flags and are not a linked production Image.

Local fixture evidence remains separate: CP1's 29 passed cases and CP3's 19 completed cases are retained under their original source/checkpoint receipts; CP3 stopped on Windows link-creation privilege error. CP4 ran only three incomplete cases, including two explicitly synthetic lstat refusal cases and one failure-preservation case. They do not establish real OS link capability. The final CI invoked zero existing fixture commands, and the parent did not replay a compiler, model or provider. The first CI remains failed; its original flat ZIP was preserved and rejected. Local reader access failures were preserved and resolved through reviewed package-only read permissions without changing parser bytes; the descriptor AI flag change is recorded privately. v63 performed zero Image/BOOT/device/reboot/provider/oracle execution operations; v57's consumed physical cycle remains unchanged.

## v62 verified full diagnostic TU static result

Source `f4dd45ff040df1a6c67b4390d17046dc6970d921` passed [CI 41189249719](https://github.com/eirblue/ios_note10p/actions/runs/41189249719), attempt 1. The parent independently verified the actual run/job/required steps, authenticated full ZIP and every extracted member, source closure, real Kbuild objects and the protected complete source archive. Parent result digest: `09e615e7b7fc6d42fe47f5dffa54a06f47fdeb0b7cf7f314c6c1a8a5cdca85a8`.

The full diagnostic `arch/arm64/mm/init.c` and its reviewed TU/Kconfig overlay compiled in default-disabled and explicitly enabled modes against real generated headers and configuration. This is an object target with explicit analysis flags, including no-inline and no machine outliner; no full production Image or BOOT image was built. Existing production C/H and the trial ABI remain unchanged.

The enabled object binds the actual pre-PM call order, guarded failure returns and every post-trial cleanup/return path. The static proof binds the complete 36,372,480-byte restore/comparison span, both hashes, byte equality, both guards and the unmasked rejection result. Clang's `bcmp` equality lowering is tied to the pinned declaration/source fallback and 50 independently decoded instruction-word fields. Neither the wrapper nor a kernel instruction model was executed.

Selected ordinary GPR instructions number 1,516; the scoped selection separately records three expected kernel-context instructions and unresolved kernel providers. It makes no whole-TU GPR or hardware FP-permission claim. The actual wrapper frame is 368 bytes. Actual header constants are `THREAD_SIZE=16384` and `IRQ_STACK_SIZE=16384`; recorded scoped frames are not a whole OS/IRQ stack bound. Generic ADT accounting retains ten possible frames, including the rejection-depth frame. No fixed external-stack allowance supplies a physical bound.

The new artifact profile retains the original 23,625,005-byte ZIP and all 2,173 members (59,593,293 expanded bytes). ZIP SHA-256: `cf4f8cf7960baabe5173d050150a6cda13aeb8ab13154d25b17e12eac988633f`. The complete 212,648,376-byte archive for kernel commit `55f042627bb7030c93550faafa117674d32b21d1` remains a protected shared input with SHA-256 `46d6a563af04e0c2ed9c96c2a1af8cab2344b458c9554b09098e6a9e7219ae4c`. The producer hashes it before compiling outside the uploaded roots; the parent independently hashes its retained copy and compares every archive-derived prerequisite byte. Generated/config and compiler-resource inputs retain separate bytes and provenance. The ZIP contains zero archive payload copies; collection creates zero hardlinks and leaves shared input bytes and identity unchanged.

Only the new external-profile synthetic cases ran locally: 18 passed. The final CI invoked zero existing fixture suites. Earlier 38/13/20/8-case evidence remains historical and tied to its original source/run or unpublished local checkpoint, without a current-source rerun claim. Failed runs 41183097021 and 41186369912 remain failed; the latter exposed a nonexistent explicit `preempt_mask.h` expectation, which was removed without dropping any real dependency.

Physical cycles, BOOT writes and reboots are zero for v62. The consumed v57 cycle was not replayed. External allocator/crypto/IRQ stack limits, actual provider availability, runtime page ownership, duration, recovery races, DMA and restoration under backup corruption remain unproven. Phone RAM writes, phone XNU execution, iOS boot and deployment readiness are not established.

## v61 actual Kbuild component projection passed

Tested source `557fa38b7ec52eb1a563860172f00e1125b60339` passed
[CI 41176433103](https://github.com/eirblue/ios_note10p/actions/runs/41176433103),
attempt 1. The independent authenticated parent reader verified actual run,
job and step success, artifact digest and complete inventories, source and
kernel input closure, original-object section bytes and exact relocations,
ABI, native emulator wheel and full observations without re-emulating. The
v61 result SHA-256 is `23f5ed8aed4c713fa349bcb20c2ed3b869d9378d6672f998ba1b1a213d18fd7c`.

The unchanged production planner/trial C/H and ABI oracle were compiled
inside the pinned reservation-only `arch/arm64/mm/init.c` translation unit
using real kernel headers, configuration and Kbuild. Fresh disabled and
enabled objects prove the default-off component and absence of incoming boot,
initcall or export references to its pure forwarding adapter. The PC ELF is
a closed projection of that actual enabled `init.o`, rooted at the explicit
adapter entry; there is no standalone core recompilation or OS provider stub.
The actual Linux initcall path is not exercised.

Analysis instrumentation is explicit: `-gdwarf-4 -fstack-usage
-ffunction-sections -fdata-sections -mllvm -enable-machine-outliner=never`,
with a pinned LLD14 non-relocatable projection link using `-O0`, garbage
collection and no relaxation. These choices change the analysis output; this
is not an unchanged production Image command. The complete 1,217-byte shared
readonly, non-executable string pool is preserved byte-for-byte and offset-for-
offset from the original object. It includes unused Linux init strings;
component references remain confined to the two evidenced relocations to the
original `name` literal. No writable or unrelated executable section is admitted.

All 57 new component gate fixtures and four actual-object adapter model cases
passed. Real payload relocation, injected comparison failure with full restore,
backup-capacity rejection and alias rejection retain the exact input geometry,
full `0x22b0000` prefix/backup/guard checks and twelve-argument target ABI.
Model CPACR_EL1 readbacks stay zero before and after all four cases. The 918
GPR-only decoded instructions are a static code count, not an executed count.
No FP trap probe, physical EL1 permission or fixed-x18 proof is inferred.

Actual compiler frames sum to 1,408 bytes. Adding the adapter's 32-byte incoming
stack-argument area gives a 1,440-byte bound for the immutable 56-byte leaf ADT,
with a 14,944-byte margin against configured `THREAD_SIZE=16384`. The generic
ADT estimate includes ten recursive frames (including rejecting depth 9) and
is 6,192 bytes. Both satisfy the unchanged component budget/margin gates.
These are scoped compiler estimates; Linux callers, allocator/crypto/PM,
asynchronous IRQ and whole-OS stack contributions remain unresolved. The
actual-header IRQ stack constant is not an IRQ stack-safety proof. No prior
2,048-byte external-stack assumption is reused.

The ten new private reader integrity fixtures passed locally in focused phases;
unchanged older suites were not replayed locally. Earlier
[CI 41174341105](https://github.com/eirblue/ios_note10p/actions/runs/41174341105)
and [CI 41175122836](https://github.com/eirblue/ios_note10p/actions/runs/41175122836)
remain failures, respectively at compiler-outline and shared-literal closure
gates. Their evidence is retained. This result builds no Image or BOOT, performs
no device action and proves no physical writer, reserved-RAM ownership, XNU
execution or iOS boot. Deployment readiness remains false; v57 remains the last
single, consumed physical diagnostic cycle.

## v60 observed kernel-option GPR profile passed

Tested source `d5b56efa5b7d9f0313fb72639db332c581e7e6b2` passed
[CI 41168995359](https://github.com/eirblue/ios_note10p/actions/runs/41168995359),
attempt 1. The authenticated parent reader bound actual run/job/step success,
artifact digest and complete inventories, reviewed source/import closure,
upstream input, exact compiler options, target ABI, native emulator wheel and
full saved observations. The v60 result SHA-256 is
`15339d5395b38e5469e0994aba90031f03e1fe203ac20354c92eddca1256b1d3`.
The tested source is distinct from result-document publication.

The new explicit `kernel-init-subset-v1` profile compiles the unchanged
production planner/trial C/H and ABI oracle with a selected option subset from
the saved v57 `init.o.cmd` (run41109866784). The historical command digest is
`6c5dcb0e7c76b5bc00533d058458632b69efca4c1330be69bd90d4201b5bca32`;
its original bytes are retained and checked locally. This is not a fresh
upstream command retrieval, the full Linux command, Linux-header translation
unit, kernel Image build or integration result. The exact nine selected options,
including `-Oz`, `-mno-implicit-float` and `-march=armv8-a+lse`, are source-pinned
in [the profile record](../device_test/relocation_trial_kernel_profile.json).
Neither `-mgeneral-regs-only` nor `-ffixed-x18` is inferred from that command.

The independent GPR-only gate parses every decoded instruction and its operand
fields. It rejects FP/SIMD operations or register classes and malformed fields,
while excluding addresses, encodings and symbol annotations from register-token
checks. All 17 new profile fixtures pass. The CI ELF decodes to 1,270 GPR-only
instruction records; the separate local compiler output had 1,193. These static
counts are not executed instruction counts. The model sets `CPACR_EL1` to zero
and verifies zero readback before and after each case. No FP-instruction trap
probe was run, and this model state does not establish real EL1 permissions.

All four new profile target cases pass: real overlapping relocation with full
restoration; transient mismatch returning INVALID with full restoration and an
unchanged result sentinel; backup-capacity rejection; and window/backup-alias
rejection. The same pinned 19,578,880-byte payload, `0x1004000` destination,
`0x22b0000` restored prefix, complete compressed observations, guard bytes,
12-argument ABI, callee-saved checks, unmapped numeric physical range and
instruction-PC bindings remain in force. A separate local private-reader run passed six new
root/profile identity checks. The earlier v59 default and historical suites
were not replayed locally; AST comparison preserves the original default
executor body and FP predicate. Verification selects the expected profile from
the caller and pinned source, never from the report itself.

This is PC execution of a kernel-option code-generation subset. It does not
access reserved physical RAM, establish ownership, resolve asynchronous-PM
ordering or init-memory lifetime, prove hardware FPU/x18 state, or execute XNU
on a phone. There are zero device, BOOT and Linux Image actions in v60. The
last physical result remains v57 with its single cycle consumed. A future
physical integration still requires its own source, context, lifetime, stack,
recovery and integrity review under the existing safety gates.

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
