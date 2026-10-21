# Registered hint sites and private Mach-O copies

`hint_sites.c/.h` provides a portable site-table validator and dispatch adapter.
`prepare_hint_copies.py` creates private research copies and manifests from the previously extracted
iOS 27.0.1 launchd, dyld and SpringBoard images. No Apple image is executed by this workflow.

## Copy preparation

- Check the original image SHA-256 against the prior inspection record.
- Reject encrypted images, out-of-bounds load commands and instruction sections outside an executable segment.
- Independently identify legacy PAC/AUT/XPAC hints using Capstone.
- Substitute the fixed-size `BRK #0x4e10` word only at identified sites, in copies under
  `note10/private/hint-copies/`. Instruction addresses and image lengths remain unchanged.
- Record unslid VA, file offset, original/replacement words and mnemonic in a JSON manifest.
- Restore every original word in memory and verify exact equality with the entire original file.
  Re-read the source to check it was not changed, then verify the written copy's hash.

Results: **dyld 130 sites; launchd 0; SpringBoard 0**.
The dyld copy's original code signature is invalidated by the changes. The zero-site copies are
byte-identical; their signature validity is not verified. These are not runnable or bootable deliverables.
Apple binaries, patch manifests and site fixtures remain excluded from Git.

## Dispatch contract

Each owning process/image supplies a trusted immutable table, validated after assigning an unsigned slide.
Validation rejects duplicate/unsorted/unaligned addresses, overflow and non-hint original instructions.
Lookup subtracts the slide and binary-searches the saved PC. Only a registered site whose fetched word
matches the reserved BRK can invoke the PAC state model. Failure preserves modeled registers and PC.
The dispatcher never fetches user memory itself.

The caller must establish image identity, address-space ownership, mapping lifetime, immutability and
fault-safe fetch. A BRK match is not an image authenticity check. Table ownership is external; no kernel
registry, loader integration or synchronization has been implemented.

## Device validation

On SM-N976N:

- All **130 real sites**, at slides 0, 0x4000 and 0x100000000, with **14,653 assertions passed**.
- Unknown-PC and changed-BRK rejection, missing-key state preservation, non-hint/duplicate/overflow table rejection.
- The Android synthetic interception harness now uses this dispatcher: **8 cores, 2,048 actual BRK exceptions**
  handled and resumed, with LR signing/authentication/strip checks passing.
- Executables and original-word fixtures were removed from the device after testing.

Only site metadata from Apple code is used in the first test. The second executes synthetic instructions.
Neither test executes the rewritten dyld image or boots XNU. Apple PAC ABI, other ISA extensions,
shared caches, signed-code policy and XNU exception integration remain unresolved.

## Reproduce

```powershell
python note10/compat/prepare_hint_copies.py
./note10/compat/build.ps1
```

These commands prepare private copies and build tests; they do not run anything on a device.
The `.sites` test fixture contains a little-endian u32 count followed by packed u64 VA/u32 original-word
records. It is decoded explicitly by the Android test and must not be cast to a padded C struct.
