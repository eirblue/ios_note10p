# v297 rootfs diagnosis result

**Diagnostic PASS; TWRP userspace remains unproven.** Source `d682cb6214e4b12a243144d804f4bf5d5c1d7f4a`; CI run `44216040772` passed. The new focused bundle passed 3 groups, 12 variants and 21 assertions. One physical cycle used one BOOT write and one host reboot; RECOVERY was unchanged.

The runtime probe found the built-in ramdisk intact, but the initramfs skip flag prevented unpacking and `/init` was absent. This identifies the next correction; it does not establish TWRP userspace success. The checksummed 90-second software request was verified, normal TWRP returned, all five partition checks passed, and the brightness setting and panel readback both showed 10.

This proves diagnosis and cooperative recovery while Linux remains running. No hardware watchdog reset or XNU execution was tested.
