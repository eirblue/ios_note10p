# Read-only fetch and branch decoder composition in v165

Four new host cases passed through the real fetch function and branch decoder. The composition preserved the tagged PC, original fetch error and entire saved frame. It returned a descriptor for a recognized branch and a zero descriptor for fetch failures or unsupported instructions.

The native compiler produced one ARM64 object and passed the BSD type regression. CI finished with a failure at the strict import audit because aggregate handling also referenced `bzero` and `memcpy`. A separately reviewed local metadata check accepted the exact four imports for that retained object after matching the XNU routine declarations, ARM64 definitions and standard build selection. The original CI result remains failed.

This establishes the bounded composition and its source-level import compatibility with the selected public reference. Native link closure, current task map ownership, exception integration, PAC key handling, target firmware ABI and runtime behavior remain unproven.
