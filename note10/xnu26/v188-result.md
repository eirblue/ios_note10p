# v188 Linux boundary-read build result

## Result

The host fixture passed all 48 planned cases across three groups in one compiler and fixture invocation. It used synthetic callbacks and made zero actual backing-storage reads. No old test suites ran. A separate local AArch64 PID1 proof passed after one compile, one symbol scan, and one proof call; that local ELF was not used as the CI Image.

The single reviewed CI dispatch completed with failure. The compiler produced the PID1 executable and its symbol scan passed, but the new validation gate rejected the file because its total extent was not divisible by 16. The requested 32-byte boundary window was in bounds. The check should constrain the requested window and relevant ELF fields without requiring padding of the whole file. No full Image build was attempted, and no retry was made.

The failed-run evidence was authenticated and safely extracted once. Its producer summary confirmed zero full Image build attempts. There were no package or device operations.

## Scope

This result covers the host synthetic fixture, a local static PID1 proof, and the published Linux RAM-rootfs CI diagnostic. It does not demonstrate an installed or booted candidate. It makes no claim about XNU execution, IOKit, DMA, or persistent storage behavior. The next revision should address the whole-file divisibility check before another CI run.

No private image hashes, device identifiers, run identifiers, raw logs, keys, or actual input fragments are included here.
