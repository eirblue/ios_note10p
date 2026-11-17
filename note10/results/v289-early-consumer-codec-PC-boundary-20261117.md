# v289 early-consumer codec PC boundary

XNU 12377.121.6 is usable as a separate iOS kernel PC development base. It is not an exact source match for iOS 26.5.2 (23F84); rootfs and runtime compatibility remain unproved.

The new single-CPU early AppleDT codec passed one grouped roundtrip assertion and rejected four direct mutations. Its inputs were synthetic. Complete platform ADT, actual CPU/DRAM ownership, the terminal caller and independent return remain unqualified. This run performed no device calls, kernel/Image/PID1 rebuild or CI.
