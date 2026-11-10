# Native user branch link closure in v166

Three ARM64 dependency objects compiled and one relocatable link passed. The merged object defines the instruction fetch, read-only composition and pure branch decoder. Internal fetch and decoder references resolved, leaving exactly the kernel imports `bzero`, `copyin` and `memcpy`.

The decoder input preserved the complete original pure function. The native build used the accepted BSD header context and retained bounded diagnostics for each compile and link stage.

This establishes native source and relocatable link compatibility with the selected public XNU reference. Current task map ownership, exception integration, PAC key handling, target firmware ABI and runtime behavior remain unproven.
