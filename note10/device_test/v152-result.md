# v152: IVA private fault-token callback drain

The fresh diagnostic source snapshots each IOMMU fault handler and token together under the existing owner lock and invokes the cached pair after unlocking. A new process-context clear API clears the pair under that lock, unlocks, and waits for an RCU grace period. IVA calls it before probe activation-failure cleanup and before remove tears down IOVMM/native resources. Existing fault registration and handler behavior, plus v151 raw-SFR mmap denial, remain unchanged.

This bounds access to the IVA-private callback token through driver unbind. Same-master set/clear must be serialized by the caller, and the platform master/owner must remain alive. Persistent master notifier records, duplicate registration on rebind, and complete platform-device destruction remain separate preexisting limits.

New host batch: **PASS, 59 assertions**, one compiler invocation and one fixture process, zero old tests replayed. Authentic notifier/clear/wrapper bodies and exact native integration/header changes are checked. Deterministic snapshot/reader models cover pair replacement, cached old readers, clear-before-return, future callback denial, and lock ordering; these are not real RCU, IRQ, SMP or hardware execution.

Native ARM64 compilation of the three modified units is pending. No Image, deployment, device operation, DMA terminal, physical owner success or XNU/iOS boot success is established. Hardware/firmware quiescence and other PM/resource closure requirements remain unresolved.
