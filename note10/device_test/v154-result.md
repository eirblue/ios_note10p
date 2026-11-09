# v154: Linux IVA mmap denial diagnostic

The diagnostic integrates the accepted v142–v153 Linux IVA and IOMMU changes, including the v150 mailbox fix, into one fresh ARM64 Linux Image. The device probe is limited to one open of `/dev/iva_ctl`, one raw mmap request with `PROT_NONE`, and close. It expects `EOPNOTSUPP` and never reads or writes the mapping. It runs only after automatic recovery return is armed. The same one-shot recovery owner handles an arming failure before the probe.

The first new host attempt compiled and ran its C fixture once, then stopped at the linked-symbol parser on the Windows model. The corrected parser follows the actual kernel linker layout and handles LF and CRLF. The separately resumed suffix ran once and passed 34 checks. The compiler and fixture were not replayed, and no old tests were run. The original failed attempt remains recorded.

Full Linux Image CI: **failed during the `vmlinux` link**. The PCIe IOMMU referenced `dhd_smmu_fault_handler`, but the Broadcom Kbuild selector omitted its implementation because the retained Android platform build environment was not supplied. The one encrypted diagnostic receipt was authenticated; GET, Node OPEN and safe extraction each ran once. No accepted Image or device package was produced, and the CI attempt was not replayed.

No device operation, DMA terminal, ownership transfer, or XNU/iOS execution occurred. The successor restores the retained Android 11/R build environment.
