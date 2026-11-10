# Retained native kernel and PC handoff

The native build compiled 1,077 current objects and completed one kernel link with no undefined symbols. Its encrypted artifact retained the executable and the source and object ownership receipts. Compact receipts preserved the required ownership fields, assembly identity and original receipt hash and size.

The normal PC handoff producer and reload passed once using the retained executable and adapter. They produced four buffers, including a 19,169,280-byte kernel memory image.

The RAM model and RAMDisk declaration remain synthetic. Actual root contents, physical backing, memory lifetime, DMA ownership, target firmware compatibility and native execution remain unproven.
