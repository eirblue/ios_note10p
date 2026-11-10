# v160: rootfs skip boundary observed

One new relocation fixture passed. One native Image CI passed with direct embedded-archive size and bounded in-Image R_AARCH64_RELATIVE initcall proof. The sealed artifact was downloaded, opened and extracted once. A contract omitted four carried header dependencies; a reviewed local summary-only remainder corrected that expectation without repeating the download, decryption or extraction. The original stopped receiver record was preserved.

One physical cycle wrote BOOT once and rebooted once. Same-boot rootfs telemetry recorded populate_seen=1, skip=1, declared archive size 3584, and zero init members processed. The pre-exec /init open returned ENOENT; PID1 entry was not observed. Pinned source places the skip branch before builtin archive unpacking and before INITRAMFS_FORCE controls external overlay handling. The successor limits skip suppression to the diagnostic builtin-route/FORCE configuration.

Automatic TWRP return and post-return partition integrity passed. The immediate brightness setter timed out; a separate same-epoch brightness-only action verified both TWRP setting and panel raw value 10, with no further BOOT write or reboot. The original spent cycle status is preserved.

No IVA userspace access, mmap, ioctl, PID1 mount, kexec or XNU execution was admitted.
