# v189 complete block read result

The v189 host fixture passed 87 synthetic cases across three groups. The local static AArch64 PID 1 proof also passed, and the reviewed source was built successfully by CI. The host fixture performed no actual backing-storage reads.

One physical Linux diagnostic cycle completed. PID 1 opened `/init` from the RAM-backed initramfs and completed one bounded 32-byte read from offset 48. The read and completion callbacks each occurred once while the owner remained live. A malformed 31-byte descriptor was denied before either provider-read or completion callbacks. The provider exposed 5,408 complete bytes from a 5,416-byte ELF file; the final 8-byte tail was not treated as a complete block.

The diagnostic returned to recovery. The cycle recorded one BOOT write and one host reboot; five-partition integrity checks passed through the retained return path. Recovery brightness was set to raw value 10 and read back in the same recovery epoch.

This demonstrates the bounded Linux RAM-rootfs file-read and completion path for this diagnostic. It does not demonstrate XNU execution, external-storage access, DMA, IOKit behavior, or a proved runtime root cause. No raw device bytes, logs, identifiers, or private hashes are included here.
