# Galaxy Note10+ native iOS port research

Target: Samsung SM-N976N (Exynos 9825), iPhone18,1 iOS 26.5.2 / 23F84.

This is an experimental source tree. An experimental arm64 XNU source-object executable link has succeeded.
There is no bootable Note10 iOS image or verified iOS boot on this device.

- [Current status](note10/STATUS.md)
- [Korean project guide](note10/README.ko.md)
- [Manual macOS compile audit](note10/xnu26/CLOUD.md)
- [Pre-device validation and blockers](note10/PREDEVICE.md)

The manual Actions workflow compiles source and retains diagnostics plus labelled experimental source-built outputs.
Firmware, IPSW contents, SDK headers, device dumps and credentials are excluded.

Reference project: https://github.com/ch1tmdgus/ios-v60 at
`3ff7ba8d7f9f59a10b0497039b684e975cee0f91`, based on
https://github.com/dipa-studio/ios-sweet . Reference project boot reports do not
establish boot success on Note10. Individual upstream license notices and the
QARMA LGPL license are retained in the corresponding source files/directories.

First device observation: [RAM-only TWRP probe](note10/device_test/README.ko.md). It collects real hardware facts; it does not execute XNU or flash partitions.


PC boot contract checks now compare real public XNU C ABI bytes, validate explicit synthetic placement, and exercise the linked SecureDT parser. [Details](note10/xnu26/BOOT-CONTRACT.md). No deployable image or physical boot is established.
