# v151: diagnostic IVA raw-SFR mmap denial

The fresh diagnostic Linux IVA source now returns `-EOPNOTSUPP` from `n145_native_mmap`. This deliberately disables future direct IVA register mappings. The existing v145 file-operations wrapper, its admission checks, sticky history, and lock handling remain unchanged. General Linux/XNU mmap and other APIs are unchanged.

The conditional compatibility decision was accepted after a scoped static check found no IVA-specific device/helper/ioctl references in the project iOS/XNU paths, actual pinned XNU source, or XNU runtime components. This does not establish third-party userspace behavior.

New host batch: **PASS, 127 assertions**, one compiler invocation and one fixture process, zero old tests replayed. The fixture uses the transformed authentic native helper and unchanged wrapper bodies. It covers unsupported results without pointer access, attached/detached/quarantined/no-context paths, sticky history, and synthetic lock balance. Host errno values and lock models are not Linux runtime or hardware evidence.

Native AArch64 controller-object CI is pending. No Image, deployment, live mapping revocation, physical test, DMA terminal, physical owner success, or XNU/iOS boot success is established. Existing PM/resource, firmware, SCORE, and all-master DMA closure requirements remain unresolved.
