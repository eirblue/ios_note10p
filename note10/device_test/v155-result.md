# v155: restore the Android 11 Linux build environment

The previous Linux diagnostic Image failed at the kernel link: its PCIe IOMMU called `dhd_smmu_fault_handler`, but Kbuild had omitted the Broadcom implementation. v155 restores the retained `PLATFORM_VERSION=11` and `ANDROID_MAJOR_VERSION=r` for build commands. The Wi-Fi and PCIe configuration stays enabled. The build must verify the actual handler definition in the same Image's symbol map.

The focused host batch passed 14 checks covering the child environment, symbol proof, and separation of the new test from the carried v154 host evidence. No old tests, C compiler, or C fixture were replayed.

Full Linux Image CI: **PASS**. The actual linked Image contains the DHD fault handler. One encrypted artifact was authenticated and safely extracted, with 36 members bound to the same build. The Image file is about 44.8 MiB and its linked extent about 53.1 MiB, within the reviewed limits. The Linux diagnostic package and paired restore ZIP were generated.

Device preflight stopped at the 10% battery requirement before any BOOT write or reboot. The mmap denial and automatic TWRP return were therefore not exercised. The physical cycle remains unconsumed. No DMA terminal, hardware ownership transfer, or XNU/iOS execution is claimed.
