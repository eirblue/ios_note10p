# Experimental software PAC model

`qarma.c` contains the standalone architected QARMA3/QARMA5 core adapted from QEMU.
`soft_pac.c` adds a deliberately restricted software sign/auth address model and adapters to the earlier branch/value components.
This is **not an Apple ARM64e_X1 implementation or a complete architectural PAuth emulator**.

## Scope

- Explicit caller-selected lower-range VA width 32–48, TBI 0/1, QARMA rounds 3/5.
- Canonical lower-range inputs only; upper-range pointer signing is rejected.
- Signature insertion/comparison outside the VA and optional tag bits, preserving range-selector bit 55 as zero.
- IA/IB branch authentication adapter using caller-supplied keys.
- IA/IB/DA/DB fixup signing adapter with separate instruction/data profiles.
- Address-diverse fixups require a validated blend callback. No default Apple blend rule is guessed; missing blend fails.
- Missing keys, malformed profiles, noncanonical pointers and rejected authentication do not produce successful results.

No hardcoded production keys are supplied. Tests explicitly provide synthetic keys.
Process key lifecycle, key isolation, exceptions, poisoned failure pointers, PAC2/EPAC/FPAC, MTE, upper ranges,
additional ARM64e_X1 rules and iOS saved-state integration are absent.
The table-based reference cipher is not side-channel hardened. No latency, sustained throughput or complete iOS workload has been measured.

## Provenance and license

QEMU source pinned at `ba93f3ae5cbe9bace0a8163843f0d678f08a3e6e`, original Linaro notices retained.
`qarma-provenance.json` records the source URL/SHA-256. The core and its API header are LGPL-2.1-or-later;
the license text is included in `licenses/LGPL-2.1.txt`. Only the cipher core was adapted, not QEMU CPU helpers.
This source attribution must be preserved in future reuse or integration.

## Verification on the actual SM-N976N

The public QARMA paper appendix A.1 includes this sigma2 QARMA64_5 known-answer vector:

```text
P  = fb623599da6e8127
T  = 477d469dec0b8762
w0 = 84be85ce9804e94b
k0 = ec2802d4e0a488e9
C  = c003b93999b33765
```

The standalone core matches C. The initial comparison incorrectly used the sigma0 answer 3ee99a6c82af0c38;
the mismatch was traced to the S-box choice and the test was corrected to the independently published sigma2 vector.
The initial mismatch record remains in `note10/private/qarma-known-answer.json`; the authoritative latest passing result is `soft-pac-test-result.json`.

Final combined device test:

- Published sigma2 QARMA5 known answer passed.
- 2,048 sign/auth roundtrips, covering 39/48-bit profiles, TBI on/off and QARMA3/5.
- 31,744 single-signature-bit changes rejected; output preserved on failure.
- Real software-model signature → authenticated branch/PC/LR transition passed.
- Format-12 authenticated rebase → software signing → authenticated branch passed for address-diversity disabled.
- Missing blend provider and missing keys rejected; no mock signer is used in these integration cases.
- 37,911 assertions passed. Temporary device executable removed.

Roundtrips and tamper checks test internal consistency; they are not independent algorithm vectors.
QARMA3 has no external known-answer vector in this test set. No comparison with Apple PAC hardware has occurred.
The accepted profile values are test parameters, not discovered Note10+/iOS 27 runtime settings.

## Remaining work

Select the actual software compatibility ABI and validate pointer masks, modifier blending and newer instruction semantics.
Implement signing/data PAC instructions and fault-safe XNU user exception integration. Verify dyld/cache loading and process key handling.
None of the tests executes an iOS program, installs a kernel or boots iOS.

Build locally with `./note10/compat/build.ps1`.

Sources: [QEMU PAuth implementation](https://github.com/qemu/qemu/blob/ba93f3ae5cbe9bace0a8163843f0d678f08a3e6e/target/arm/tcg/pauth_helper.c),
[The QARMA Block Cipher Family](https://eprint.iacr.org/2016/444.pdf).
