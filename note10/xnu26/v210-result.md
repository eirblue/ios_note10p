# v210 Native-Owned Prepare

The v210 source was published at commit `5efa4cee84873e69cde58a0452d8b0719c7da7c1`. The focused fixture passed six groups across 16 variants, with 33 assertions.

[CI run 43140014924](https://github.com/eirblue/ios_note10p/actions/runs/43140014924) completed with failure. Toolchain installation completed, but native preparation stopped when the accepted initramfs parser rejected the observed rootfs/parser input. The failure occurred before PID1 compilation or the Linux Image build.

No producer artifact was authenticated or received, and no package or device operation followed. This result reports only the fixture and CI failure; it does not establish a successful native build or physical execution.