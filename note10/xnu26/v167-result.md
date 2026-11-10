# RAMDisk consumer extent boundary in v167

Five new PC cases passed through the RAMDisk declaration producer. The producer now limits an extent to `0xfffff000` bytes, matching the largest aligned size preserved by the public memdev consumer's current 32-bit byte reconstruction. The valid boundary retained the exact device tree encoding and left the input tree unchanged. Four larger declarations were rejected, including the retained full image lengths.

This establishes a source-bound producer guard for the selected public XNU reference. Full image block backing, mapped memory ownership, lifetime, root mounting and target firmware behavior remain unproven.
