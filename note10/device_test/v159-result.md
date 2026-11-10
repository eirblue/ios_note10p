# v159: rootfs materialization observation build

The new focused PC transformation and observation-decoder fixtures passed once. One native Image CI completed compilation but failed the new linked rootfs size/initcall assertion. Its sealed failure evidence was authenticated. No v159 device cycle was admitted or executed.

Source investigation found that this ARM64 link uses --no-apply-dynamic-relocs. Relative initcall pointers are filled from relocation addends during boot, so comparing the raw Image slot directly with populate_rootfs was an invalid assumption. The failed artifact did not retain the individual predicate values, so the exact rejected conjunct is not established.

The successor retains the original rootfs behavior and verifies the bounded in-Image relative relocation as well as the declared archive size. It records individual proof observations before rejecting. No failed CI or consumed physical cycle is replayed.
