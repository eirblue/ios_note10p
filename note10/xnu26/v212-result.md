# v212 freestanding PID1 footprint

The reviewed v212 source was published to `main` at [`3f67fdf`](https://github.com/eirblue/ios_note10p/commit/3f67fdf066401a3e22780e7ea25971485afe7a61). [CI run 43170811022](https://github.com/eirblue/ios_note10p/actions/runs/43170811022) completed successfully.

The new host fixture passed 5 groups, 16 variants, and 48 checks. The local receive step authenticated the 13-member evidence set, and the package step completed.

## Measured footprint

- PID1: 7,704 bytes; 713,456 bytes smaller than v211. The measured mapped span is 8,192 bytes.
- Image: 46,284,812 bytes; 2,048 bytes larger than v208 and 720,896 bytes smaller than v211.
- Linked extent: 55,005,184 bytes; 4,096 bytes larger than v208 and 720,896 bytes smaller than v211.
- The planned reservation remains 32 MiB larger than v208; no native source allocation was measured.

This demonstrates the PC-side footprint objective only. A read-only device preflight stopped at the battery readiness gate before partition integrity checks or staging. No BOOT write or reboot occurred. XNU was not executed. The result does not establish native source ownership or lifetime, active XNU mapping, or qualified XNU return. The 32 MiB reservation acknowledgement was received, but the v212 one-shot physical attempt is spent and cannot be replayed. Any later build requires a fresh battery readiness check of at least 10% and the remaining preflight gates.