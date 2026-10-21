# Pointer value computation and import metadata

`fixup_value.c` computes format-12 pointer values from an image base and a caller-provided resolved bind-target table.
`import_table.c` reads import metadata from a bounded LC_DYLD_CHAINED_FIXUPS blob.
Neither component maps or modifies images, executes dyld, searches a shared cache, or implements PAC cryptography.

## Implemented

- Unauthenticated rebase values, including high8 reconstruction and image base addition.
- Bind-target selection and signed chain addends, with explicit underflow/overflow errors.
- Authenticated rebase/bind dispatch to an external signing backend, carrying key, diversity, address-diversity flag and actual slot address separately.
- Missing signing backend returns NEEDS_SIGN; rejected signing leaves the result unchanged.
- Authenticated null binds remain zero without signing, matching the observed dyld implementation.
- Import formats 1, 2 and 3: library ordinals, weak flags, names and signed 32/64-bit import addends.
- Correct special negative library ordinal range while retaining large positive ordinals.
- Rejection of table/name bounds errors, empty/unterminated names, reserved bits, overlapping tables and unsupported versions/compressed symbol pools.

Bind targets must already include import-table addends. The decoder's library/name metadata supplies information to a future symbol resolver;
the resolver itself is not implemented. No placeholder addresses are used by production code.
Callers must retain ownership of immutable input buffers while borrowed name pointers are in use.
The stricter overflow/table-order checks can reject malformed or unsupported layouts instead of emulating unchecked wraparound.

## Validation performed

On the connected SM-N976N:

- 24,322 pointer records compared against the independent compiled Apple field layouts and controlled bind-target/signing fixtures.
- All 706 actual import entries read: launchd 705, SpringBoard 1, dyld 0.
- Synthetic import formats 2/3, negative/special library ordinals and INT32_MIN/INT64_MIN/INT64_MAX tested.
- Missing signer, failed signer, null weak targets, arithmetic overflows and malformed import data tested.
- 89,186 assertions passed; temporary device fixtures/executable removed.
- Signing tests use an explicitly fake callback to test data/control flow. They do not verify real signed pointer values.

The three source components compile to freestanding ARMv8.2 ELF objects and Apple arm64 Mach-O objects.
Kernel linking, PAC cryptography, actual symbol resolution, XNU integration and iOS execution remain unverified/unimplemented.

## Reproduction

```powershell
python note10/compat/fetch_fixup_reference.py
python note10/compat/collect_fixup24.py
./note10/compat/build.ps1
```

The collector additionally writes `launchd-fixups.bin`, `dyld-fixups.bin` and `SpringBoard-fixups.bin` into the private directory.
The device result is `note10/private/loader-value-test-result.json`.
Apple reference header is pinned by `fixup-reference.json` and is test-only.

Behavior reference: [Apple MachOLoaded.cpp](https://github.com/apple-oss-distributions/dyld/blob/main/common/MachOLoaded.cpp), fixupAllChainedFixups handling of ARM64e_USERLAND24.
