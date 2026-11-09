# v155: restore the Android 11 Linux build environment

The previous Linux diagnostic Image failed at the kernel link: its PCIe IOMMU called `dhd_smmu_fault_handler`, but Kbuild had omitted the Broadcom implementation. v155 restores the retained `PLATFORM_VERSION=11` and `ANDROID_MAJOR_VERSION=r` for build commands. The Wi-Fi and PCIe configuration stays enabled. The build must verify the actual handler definition in the same Image's symbol map.

The focused host batch passed 14 checks covering the child environment, symbol proof, and separation of the new test from the carried v154 host evidence. No old tests, C compiler, or C fixture were replayed.

Full Linux Image CI: pending. The device diagnostic is limited to IVA mmap denial and automatic TWRP return. No device action, DMA terminal, or XNU/iOS execution is claimed.
