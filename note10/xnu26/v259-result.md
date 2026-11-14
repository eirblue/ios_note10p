# v259 result

One host C++17 compile and one fixture process passed: 8/8 new assertions for the owned-copy RAM nub factory. The cases cover copy isolation and backing ownership, preallocation limits and geometry, and cleanup after allocation or initialization failures. The compile used the actual new factory and nub C++ sources with narrow synthetic kernel and I/O shims.

This is a conditional host-only result. It is not an XNU SDK build or native-kernel link. Native ABI compatibility, factory inclusion in the native kernel, runtime backing ownership, provider registration, activation, and physical behavior remain unverified. No native-target compile, kernel link, device query/write, BOOT/RECOVERY write, or reboot occurred.
