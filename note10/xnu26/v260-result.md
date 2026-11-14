# v260 result

Four new v260 fixture assertions passed on the host. One CI run compiled the owned-RAM factory target with the native SDK into a 976-byte object. The CI dispatch, artifact download, and authenticated artifact open each occurred once. Native source generation and host configuration preparation also ran; their combined process count was not captured.

This is a single factory-object compile result, not a native-kernel link or full XNU build. No other XNU object was compiled. Kernel inclusion, native ABI integration, provider registration, activation, runtime RAM ownership or growth, and physical behavior remain unverified. No device query/write, BOOT or RECOVERY write, or reboot occurred.
