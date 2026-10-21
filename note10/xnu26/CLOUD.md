# Manual macOS compile audit, without owning a Mac

The current Windows compiler lacks XNU allocator type-analysis builtins needed by many sources.
A manual GitHub Actions workflow now runs Apple Clang on a hosted macOS runner. It is a compile audit and **does not produce a flash image or promise a successful kernel build**.
GitHub documents the `macos-26` runner in its [runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

Files: `.github/workflows/note10-native-compile.yml` and `cloud_compile.py`.

- Trigger: manual `workflow_dispatch` only. No automatic push/PR job is added.
- Permissions: repository contents read; checkout does not persist credentials. Timeout: 30 minutes.
- Fetches public source by pinned commit/archive hash and applies the prepared patch series.
- Reads both pinned KDK declaration payloads after mounting the image read-only; no installer is run.
- Builds the real config tool on macOS, generates native feature configurations and source header exports.
- Uses `xcrun` Apple Clang and the installed SDK for C, C++ and assembly compilation.
- Generates Mach MIG headers/C sources, BSD syscall inputs and DriverKit IIG inputs with native tools.
- Generates assembly offsets from actual genassym.c and compares them with the upstream sed rule.
- Audits object symbols, merges objects and attempts an experimental static ARM64 link using upstream layout options.
- Uploads diagnostics and separately labelled native source-built experimental outputs. Original IPSW/Samsung firmware, SDK/KDK headers and device data are excluded.

PC validation checks the manual workflow shape, source archive checksum and SoC MASTER outputs for
three variants, matching the existing results in an isolated fixture. The remote job has now run.

Verified baseline [run 39530381182](https://github.com/eirblue/ios_note10p/actions/runs/39530381182):
Apple Clang 21.0.0 from Xcode 26.6 supports both XNU allocator builtins. Existing selected source
files compiled: C 863/863, C++ 110/110, assembly 19/19. All 68 native Mach interface headers
were generated and 148 real structure offsets were produced. That baseline still skipped
40 generated C files and 19 generated C++ files; later runs address those separately.
Later runs compile the generated inputs too. [Run 39531554122](https://github.com/eirblue/ios_note10p/actions/runs/39531554122)
compiled C 903/903, C++ 129/129, assembly 19/19 and merged 1,051 objects with `ld -r`.
There are 316 unresolved external symbol names; see [LINK.md](LINK.md).
The final workflow adds a strict source-compilation gate: failed or skipped selected inputs
make it fail. Candidate architecture errors are reported separately. A green source audit
never means a bootable kernel has been built.

## Designated remote build

GitHub device authentication was completed as `eirblue`. The user designated
`https://github.com/eirblue/ios_note10p` for publishing the Note10 source and dispatching
this workflow. The reference remote `ch1tmdgus/ios-v60` remains unchanged.
A source-only snapshot excludes firmware, local hardware dumps, SDK files, credentials
and the reference project's unrelated workflows. Run status is recorded in STATUS.md.

The manual workflow must exist on the designated repository's default branch before
its dispatch is available. Authentication credentials remain in GitHub CLI's local
credential storage and are never copied into this repository or artifacts.

This step only supplies an Apple build environment. Physical RAM/granule/cache/handoff evidence,
complete platform support, PAC/userland integration, drivers and actual boot verification remain separate work.

Latest verified static link: [39559172237](https://github.com/eirblue/ios_note10p/actions/runs/39559172237). All 1,071 objects compiled; the experimental 18.5 MB arm64 MH_EXECUTE has no undefined symbols. See [LINK.md](LINK.md) for synthetic inputs, layout warnings and deployment limits.
