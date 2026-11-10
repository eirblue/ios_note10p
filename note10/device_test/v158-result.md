# v158: builtin PID1 entry diagnostic

The reviewed entry-only PID1 passed one host build and one focused fixture. One ARM64 Image CI passed and its sealed artifact was authenticated.

One physical diagnostic installed BOOT once and rebooted once. The same-boot pre-exec observation found that opening /init returned ENOENT; PID1 entry was not observed. This narrows the failure to pathname lookup. It does not establish why the embedded initramfs did not produce a reachable /init.

Automatic TWRP return and the post-return partition integrity gates passed. The cycle retained its failed, spent status because the immediate brightness command timed out. A separate brightness-only recovery action confirmed TWRP setting and panel raw brightness at 10 in the same recovery epoch, with no additional BOOT write or reboot.

No IVA userspace access, mmap, ioctl, mount, kexec, or XNU execution was admitted. The spent build will not be replayed. The successor adds bounded rootfs materialization observations while preserving the original unpack and return paths.
