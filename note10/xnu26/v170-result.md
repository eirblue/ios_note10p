# Patched memdev in the native kernel link

The new native build compiled 1,077 current objects and passed one final kernel link. The patched memdev unit occupied its standard BSD inventory slot. All 27 of its imports bound to real source-owned kernel providers, and the final symbol table contained its eight exports and those provider names once each. The kernel had no undefined symbols.

The patch widens byte extents before shifting and bounds character transfer counts before conversion to int. The conservative RAMDisk producer limit remains `0xfffff000` bytes.

This establishes integration with the selected public XNU reference. Target firmware compatibility, native execution, root backing contents and mapped memory lifetime, DMA ownership and root mounting remain unproven.
