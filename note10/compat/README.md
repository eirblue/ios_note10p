# Authenticated branch compatibility component

This is an initial portable C component for the Note10+ iOS 27 investigation.
It is **not a working PAC emulator, an XNU patch, or a bootable port**.
The format-12 pointer metadata decoder/page walker is documented separately in [FIXUP24.md](FIXUP24.md).
The pointer value/import metadata components are documented in [LOADER-VALUES.md](LOADER-VALUES.md). These still require a real signing backend and symbol resolver.
An experimental restricted software signing/authentication model is now available: [SOFT-PAC.md](SOFT-PAC.md). It has not been validated as an Apple ARM64e_X1 backend.
Legacy PAC/AUT/XPAC decoding and explicit register-state execution: [PAC-INSTRUCTIONS.md](PAC-INSTRUCTIONS.md). Hint interception and XNU traps remain unimplemented.

## Implemented

- Exact decoding of BRAA/BRAAZ/BRAB/BRABZ, BLRAA/BLRAAZ/BLRAB/BLRABZ and RETAA/RETAB.
- Register/PC transition model with a mandatory external authentication callback.
- SP versus XZR distinction, IA versus IB key selection, zero modifiers and LR alias handling.
- Missing authentication callback returns NEEDS_AUTH. Rejected authentication and malformed targets do not update guest state. No permissive pointer stripping backend is supplied.

The model does not implement cryptography, process keys, signing/data PAC instructions,
ARM64e_X1 extensions, PSTATE/BTYPE/BTI, virtual address validity checks or trap/fault delivery.
The authentication backend must enforce its process address rules and return a verified target.
Callbacks must not mutate or alias the supplied state. All calls require a valid decoded state
snapshot whose ownership is controlled by the future trap integration.

## Validation performed

- Clang 9.0.8 Android API 24 build with warnings treated as errors.
- 288,009 oracle records, including 253,145 instruction words from the original iOS 27 launchd/dyld/SpringBoard sections.
- Capstone oracle generated independently from the decoder, plus exhaustive register variants, encoding mutations and seeded random words. 5,849 supported records including repeated instructions from real files.
- Actual SM-N976N execution: 887,451 assertions passed. Test files removed after execution.
- State transition tests use an explicitly test-only authentication callback. They do not test real PAC cryptography.
- Freestanding ARMv8.2 ELF object compiled with general registers only; llvm-nm reported no undefined symbols.
- Apple arm64 Mach-O object compiled. No XNU link or kernel execution has occurred.

Oracle/results are private generated files:
`note10/private/auth-branch-oracle.json`, `auth-branch-oracle.bin`, `auth-branch-test-result.json`.
The corpus is generated from Apple binaries and is excluded from Git.

## Reproduce the PC build

From the project root:

```powershell
python note10/compat/generate_oracle.py
python note10/compat/fetch_fixup_reference.py
python note10/compat/collect_fixup24.py
./note10/compat/build.ps1
```

The generator requires the extracted userland files and reports from the preceding analysis.
It uses Capstone from `host-tools/python-packages`. Build.ps1 accepts `-NdkRoot` for a different Android NDK.
These commands build locally; they do not transfer files to a device.

## Required before XNU integration

1. Obtain and identify the target XNU source/build environment. Do not assume an older sleh.c has an identical saved-state layout or fault path.
2. Add an audited user instruction fetch path (fault-safe copyin, four bytes, saved user PC), not an unchecked kernel pointer dereference.
3. Implement and validate the real authentication/signing backend, process key lifetime, pointer formats and the additional instructions needed by ARM64e_X1.
4. Map the register model through the target kernel's saved-state accessors, including exception delivery, PSTATE/BTYPE/BTI and signal/thread races.
5. Verify complete loader/chained-fixup ABI and shared cache compatibility before attempting iOS launchd.

No integration or compatibility success is implied by the decoder tests.

Encoding reference: [Arm instruction specification](https://documentation-service.arm.com/static/685eb35c3cb5b729562ba389), BRAA/BLRAA/RETAA families.
The implementation was written for this project; third-party disassembler code is not embedded in it.
