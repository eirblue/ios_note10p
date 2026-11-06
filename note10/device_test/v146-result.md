# v146 IVA user-read failures: host result

Both existing get_user calls in the initialization and clock-setting helpers now check their result. A failed read returns -EFAULT before initialization/PM delegation or the clock helper's OPP, QoS, rate logging, clock reads and state changes. Each path reads once. The existing outer ioctl command trace and successful-read behavior remain unchanged; a fault may zero the fetched value and is not described as an uninitialized-value proof.

The new GNU89 native-body fixture passed 168 assertions with one transform, one compiler invocation and one fixture process, including one transform refusal check. It covers both complete helpers and the existing ioctl dispatch body, with instrumented backend effects. Previously passed tests were not rerun.

The host fixture uses an explicit pointer-width bridge only for its extracted ioctl copy; production ABI is unchanged. This result does not establish target kernel integration or complete DMA, firmware or resource termination. No Image, package or device action occurred; the physical IVA owner gate remains closed.
