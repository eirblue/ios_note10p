# PAC instruction decoder and explicit state model

`pac_instruction.c` implements 31 legacy instruction forms using the restricted software PAC profile.
It is a manually invoked register-state model, not an installed instruction trap handler or a complete PAuth emulator.

## Implemented

- Register forms PACIA/IB/DA/DB and AUTIA/IB/DA/DB.
- Zero-modifier forms PACIZA/IZB/DZA/DZB and AUTIZA/IZB/DZA/DZB.
- XPACI/XPACD.
- Thirteen hints: PACIA1716/PACIB1716/AUTIA1716/AUTIB1716, PACIAZ/PACIBZ/AUTIAZ/AUTIBZ,
  PACIASP/PACIBSP/AUTIASP/AUTIBSP and XPACLRI.
- Key and instruction/data profile selection; XZR destinations; SP and zero modifiers; register alias snapshots.
- Successful model execution advances PC by four; errors leave modeled registers/PC unchanged.
- Missing keys are rejected. Strip uses the lower-range profile without requiring a key.

The software model's strict authentication failure is not full architectural poisoned-pointer or FPAC behavior.
PSTATE/BTYPE/BTI, feature enable controls, CPU-specific instruction variants and new ARM64e_X1 instructions remain outside scope.
All prior limitations in SOFT-PAC.md still apply.

## Independent decoder validation

- Oracle: Capstone mnemonic/operand decoding, separate from the C bitmask decoder.
- Exhaustive register combinations, zero/strip destination variations, encoding mutations, deterministic random words,
  and original launchd/dyld/SpringBoard instruction sections.
- 291,766 records, 11,480 positive records including duplicates from real code.
- 2,955 original supported instructions, of which 130 are hint encodings.
- Original section words that the external decoder cannot recognize are not treated as implemented.

Actual SM-N976N execution: **932,743 assertions passed**.
Tests include real software-model sign→auth, hint state-model pairs, IA/IB/DA/DB selection, SP/zero,
register aliases, strip, invalid/missing keys, malformed PC, XZR destinations and state preservation on failure.
Temporary device test executable and corpus were removed afterward.
These tests execute Android C code; they do not execute patched iOS instructions or boot XNU.

## Hint interception is a separate blocker

On pre-PAuth CPUs, some PAC/AUT hints execute as NOP without producing an undefined-instruction exception.
Thus an undefined-instruction trap handler alone cannot invoke this software model for all relevant instructions.
The iOS binaries already examined contain 130 such hint instructions. Instrumentation, validated code rewriting,
or another interception strategy would be required. An Android-only synthetic BRK interception experiment
has since passed on the target device; see [HINT-INTERCEPT.md](HINT-INTERCEPT.md).
Actual iOS instrumentation and XNU integration remain unimplemented. Merely adding this decoder to XNU is insufficient.

Reference: [Arm programmer's guide, section 3.4 NOP space](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Providing%20protection%20for%20complex%20software.pdf).

## Reproduction

```powershell
python note10/compat/generate_pac_oracle.py
./note10/compat/build.ps1
```

Requires the previously extracted userland reports/files and local Capstone package.
Outputs remain in `note10/private/pac-instruction-oracle.{bin,json}` and `pac-instruction-test-result.json`.
Build emits Android test ELF, freestanding ARMv8.2 ELF object and Apple arm64 Mach-O object; no device execution is automatic.
