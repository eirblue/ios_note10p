# ARM64e USERLAND24 pointer metadata component

`fixup24.c` decodes format 12 pointer metadata and walks bounded 4 KiB/16 KiB pages.
It does not perform relocations, load libraries, sign pointers, or modify an image.

## Implemented

- Authenticated/unauthenticated rebase and bind fields.
- Full 24-bit bind ordinals, reserved-zero rejection, signed 19-bit addends.
- IA/IB/DA/DB key identifiers, diversity, address-diversity flag, high8 and target offsets.
- Eight-byte next stride and end markers.
- Page bounds before every pointer read, malformed encoding rejection, explicit visitor-stop handling.
- No-start pages supported; multi-start pages explicitly rejected. No permissive fallback to another format.

The API returns encoded metadata, not usable signed pointers. A future loader must resolve the import table,
rebase according to the image's address rules, derive the proper authentication modifier, sign with the process key
and commit only after validation. Chain traversal stops are not transactions: visitors already invoked remain invoked.

## Original iOS 27 data

| File | Total | Auth bind | Auth rebase | Bind | Rebase |
|---|---:|---:|---:|---:|---:|
| launchd | 2471 | 909 | 389 | 115 | 1058 |
| dyld | 1835 | 0 | 657 | 0 | 1178 |
| SpringBoard | 1 | 1 | 0 | 0 | 0 |

`collect_fixup24.py` reads original file-backed Mach-O segments with bounds checks. It validates format,
page starts, segment VM offsets, reserved bind bits, import ordinal limits and each chain's page/file boundary.
It does not mutate input. Generated Apple pointer/page fixtures stay in the Git-excluded private directory.

## Validation performed on SM-N976N

- 24,322 records, including all 4,307 real fixups, seeded random words and field boundary cases.
- Reference: original Apple C bitfield structs, compiled independently from the project's bitmask decoder.
- Reference pinned to dyld commit e9da5ae571b4191dcdbcfd827363f19847c84561; SHA-256 and URL in fixup-reference.json.
- Nine original pages traversed in C; 4,307 visits matched the separately collected counts and page bytes stayed unchanged.
- Directed malformed-input/visitor-stop/empty-page tests included.
- 172,836 assertions passed. Device test files were removed after result collection.
- SpringBoard's single auth-bind24 was additionally inspected with ipsw's fixup printer:
  slot 0x100004008, raw 0xc001000000000000, key IA, address diversity enabled, diversity 0, ordinal 0.

No PAC cryptography or XNU execution was tested. This is a pointer metadata component, not a complete loader.
The freestanding fixup24 ELF object references memcpy for the output structure copy; a future kernel link must supply its normal memcpy implementation. Object compilation is not a standalone link test.

## Reproduce

```powershell
python note10/compat/fetch_fixup_reference.py
python note10/compat/collect_fixup24.py
./note10/compat/build.ps1
```

The build uses the existing Android NDK and verifies the reference-header hash.
It emits Android test executables, freestanding AArch64 ELF objects and Apple arm64 Mach-O objects locally.
It does not automatically transfer or execute anything on a device.

Generated records/results: `note10/private/fixup24-corpus.json`, `.bin`, `.pages`, and `fixup24-test-result.json`.

Reference layout: [Apple dyld fixup-chains.h](https://github.com/apple-oss-distributions/dyld/blob/e9da5ae571b4191dcdbcfd827363f19847c84561/include/mach-o/fixup-chains.h).
The original Apple header is used only by tests and remains downloaded with its license; it is not embedded in fixup24.c.
