# RAMDisk reservation checks across handoff calls

Six focused PC test groups passed once. Bundle construction and reload now validate the decoded RAMDisk extent against the shared conservative size limit, modeled RAM, occupied ranges and a containing aligned reservation. The selected reservation must also fit wholly inside modeled RAM. Raw ADT bypasses and manifest-only reservation tampering were rejected.

The bundle retains its four buffers and synthetic scope. These checks preserve a caller-declared spatial relationship. Actual backing contents, native allocator exclusion, memory lifetime, DMA ownership and root mounting remain unproven.
