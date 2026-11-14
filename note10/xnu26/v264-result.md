# v264 result

Two new v264 fixture assertions passed on the host. The reviewed source was published, and its single CI run succeeded. The native artifact was authenticated: it linked 1,080 units, compiled one auxiliary `genassym` target, one factory target, and one media target, and linked once. Native capture passed.

Package creation failed the fixed carrier-member size limit. The member measured 6,213,764 bytes against a 6,209,440-byte limit, exceeding it by 4,324 bytes. The native span and raw payload fit their existing bounds. One materialization and one compression occurred; the carrier image was not read. No trim or recompression was attempted, and no package was produced.

No v264 candidate was installed and no device action followed. Records and physical stages were not run; BOOT writes, reboots, and XNU transfers remain at zero. The latest installed baseline remains v262. No native consumer, factory, or provider activation was invoked on the device.
