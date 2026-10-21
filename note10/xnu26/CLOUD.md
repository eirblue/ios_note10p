# Manual macOS compile audit, without owning a Mac

The current Windows compiler lacks XNU allocator type-analysis builtins needed by many sources.
A manual GitHub Actions workflow is prepared to try the available Apple Clang on a hosted macOS
runner. It is a compile audit and **does not produce a flash image or promise a successful kernel build**.
GitHub documents the `macos-26` runner in its [runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

Files: `.github/workflows/note10-native-compile.yml` and `cloud_compile.py`.

- Trigger: manual `workflow_dispatch` only. No automatic push/PR job is added.
- Permissions: repository contents read; checkout does not persist credentials. Timeout: 30 minutes.
- Fetches public source by pinned commit/archive hash and applies the prepared patch series.
- Reads pinned KDK SDK declaration payload after mounting the image read-only; no installer is run.
- Builds the real config tool on macOS, generates native feature configurations and source header exports.
- Uses `xcrun` Apple Clang and the installed SDK for selected or broad C compilation.
- Uploads diagnostics/reports only. Original IPSW/Samsung firmware, SDK/KDK headers and device data are excluded.

PC validation checks the manual workflow shape, source archive checksum and SoC MASTER outputs for
three variants, matching the existing results in an isolated fixture. **The macOS job has not run.**
SDK/tool availability, Apple-Clang feature support and remaining source errors must be checked by that run.

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
