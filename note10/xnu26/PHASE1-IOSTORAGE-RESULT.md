# Phase 1 public IOStorage declaration

The [macOS CI run](https://github.com/eirblue/ios_note10p/actions/runs/42573991652) compiled the declaration once with macOS SDK 26.5 and an ARM64 iOS 26.5.2 target. The compiler accepted all 14 overrides against the pinned public IOStorageFamily headers and verified that the declared subclass is concrete. The workflow returned a source-bound JSON result.

The check establishes the public C++ declaration boundary. The Exynos block provider, IOMedia registration and APFS root mount still require integration. The run performed no device operations.

The subsequent [PIO bridge SDK run](https://github.com/eirblue/ios_note10p/actions/runs/42581228925) compiled the bridge once with macOS SDK 26.5. The checked code connects the read request core to IOMemoryDescriptor preparation, copy and cleanup, followed by IOStorage completion. The separate PC request fixture passed 10 cases, including rejection before admission, short reads and backing failures.

The PIO result covers source compatibility with the SDK. Linking, service registration, inline completion safety at the final caller, and APFS mounting still require verification.
