# v203: read-only PIO nub host chain

The host fixture passed seven focused cases across three groups. Five compile processes ran: four compiled unchanged dependencies and one compiled the new fixture. The host linked once and ran once. The fixture exercised the nub, PIO bridge, and C read core data, status, and completion path with a synthetic descriptor. The reviewed source commit is `73d43b023a7fae79ad18c950a7ee48ba454bc822`.

This is a host-only result. No SDK target, CI run, kernel-page read, old test suite, or device action occurred. It does not establish IOKit runtime behavior, provider registration or ownership, firmware compatibility, activation, or device behavior. The new nub is separate from the retained v200 native kernel.
