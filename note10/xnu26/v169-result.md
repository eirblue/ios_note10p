# Patched memdev source acceptance in v168 and v169

Nine host arithmetic cases passed with 31 checks for widened RAMDisk byte extents and bounded character transfer counts. The first native cycle stopped during BSD context binding before compilation. Source inspection found that its metadata guard rejected a legitimate generated macro expression.

The v169 cycle passed all ten context predicates, applied the exact source patch and compiled one ARM64 memdev object. Its full compiler arguments retained the generated expression while the public metadata carried a safe projection and full hash. Three new projection test groups passed.

CI finished with a failure at the export audit because the seven-name expectation omitted the global `mdev` array. A separately reviewed local metadata predicate accepted the exact eight observed exports against the pinned original and patched source. The original CI result remains failed. The 27 kernel imports remain unresolved observations at this stage.

This establishes the bounded source repair and native object acceptance with the selected public XNU reference. Kernel link integration, root backing ownership and lifetime, runtime behavior and target firmware compatibility remain unproven. The conservative RAMDisk producer limit remains `0xfffff000` bytes.
