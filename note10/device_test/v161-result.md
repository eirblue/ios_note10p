# v161: embedded initramfs and PID1 entry observed

One focused host build tested all eight combinations of the three existing diagnostic settings. Only NOTE10_V154_LINUX_DIAGNOSTIC plus NOTE10_BUILTIN_INIT_ROUTE plus INITRAMFS_FORCE suppress the skip-initramfs assignment. Other configurations and nonempty-argument rejection retain the original parser behavior.

One ARM64 Image CI passed; the sealed artifact authenticated. Same-Image evidence binds the transformed parser, effective/generated settings, compiled rootfs source, embedded archive and relative initcall relocation. Seven new mocked maintenance cases passed once; prior fixtures were not replayed.

One physical cycle wrote BOOT once and rebooted once. Same-boot telemetry recorded populate_seen=1, skip=0, one init member and successful init open. The N158PID1 entry record matched the fresh build/cycle/boot identity. Automatic TWRP return, all-five post-return integrity gates and both brightness readbacks at raw10 passed. The cycle is consumed and will not be replayed.

This proves the bounded Linux diagnostic PID1 route. It does not prove XNU or iOS execution, a UI, or hardware DMA ownership transfer. No IVA userspace probe, mmap, ioctl, PID1 mount, kexec or XNU execution was admitted.
