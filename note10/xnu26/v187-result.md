# v187 Linux nonzero-read and EOF-denial result

## Result

The v187 diagnostic completed one Linux boot cycle and verified both the nonzero read and end-of-file denial paths in the same boot. The scope was the PID1 provider running in a RAM root filesystem with the existing read request and range core. No XNU, DMA, or IOKit execution was involved.

## Host and build evidence

The host fixture compiled and ran once. Its original result remains recorded as failed because one decoder assertion rejected a synthetic denial-frame mutation. The successful C-side assertions completed 12 request-path and 4 EOF-denial checks. A corrected decoder-only continuation then passed 26 checks using the already-captured synthetic frame; the fixture and compiler were not rerun. Together these results cover the planned 42 cases across three groups. The host fixture made zero actual backing-storage reads; the later physical PID1 read described below did occur. No old test suites ran.

A local AArch64 PID1 was compiled once. An initial proof call stopped before the proof body because an argument was omitted; the retained ELF was then checked once with the complete proof arguments and passed. No rebuild or repeat symbol scan was performed. CI built and linked the reviewed source profile, and the authenticated artifact was received and extracted once. Package preparation completed once.

## Physical observation

The read request was admitted at byte offset 16 for 64 bytes. The provider returned all 64 bytes and delivered one completion callback with success status. The request at the first end-of-file block was denied without read or completion callbacks. The offset-16 window witnessed the ELF header tuple ET_EXEC (2), EM_AARCH64 (183), and EV_CURRENT (1). Build metadata separately identified the full file as ELF64 little-endian AArch64.

The cycle used one BOOT write and one reboot. The device returned to recovery, the diagnostic and read-completion checks passed, and all five partition integrity checks ran in the retained return gate. Recovery brightness was set to raw value 10 and read back in the same recovery epoch.

## Limits

This result covers the v187 Linux RAM-rootfs read provider and its same-boot completion and EOF-denial behavior. It makes no claim about XNU execution, IOKit, DMA, or persistent storage behavior. No private image bytes, device identifiers, raw logs, keys, or actual input fragments are included here.
