# Native user instruction fetch object passed in v164

One ARM64 Mach-O object compiled with the real generated XNU headers and the reviewed Apple toolchain. Its only external definition is `n10_fetch_user_instruction`, and its only unresolved import is `copyin`. The BSD type regression passed in the same compilation. The CI result was received once and matched the reviewed source and artifact digest.

The earlier failure came from mixing BSD types with standalone Mach libsa types. The new mode omits `MACH_KERNEL_PRIVATE` for this translation unit and retains the other private kernel declarations. The regression checks the actual `dev_t` and `daddr_t` identities and rejects standalone libsa types.

The result covers compile compatibility with the selected public XNU reference and generated configuration. Target firmware ABI, current task map ownership, exception integration, PAC key handling and runtime behavior remain unproven.
