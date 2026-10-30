# XNU runtime planner: PC-only kernel component plan

v55 prepares a default-off `CONFIG_NOTE10_XNU_RUNTIME_PLAN` integration in the
pinned Linux reservation translation unit. Actual disabled/enabled Kbuild
`arch/arm64/mm/init.o` compilation and focused operator checks are pending.
The verified v54 hosted planner and its previous results remain the baseline.

The source-only canonical reservation adapter reproduces the pinned original
`init.c` include/call transform, a fresh build identifier, and the exact original
reservation extension. It does not execute the older preparer or generate its
minimal-init/CPIO. Disabled preparation leaves this explicit reservation-only
source/config baseline byte-identical. Enabled preparation adds guarded includes
and a guarded call with a default-n option; the existing phone/PM build chain is
unchanged.

The wrapper admits only the current boot's successful reservation, a base at
least 2 GiB with 32 MiB alignment and a 40-bit bounded 256 MiB extent, and a full
valid reserved-page count. It passes that numeric base, hash-bound actual payload
geometry and a tiny explicitly synthetic ADT to `n10_rt_plan`, using local output.
The bounded `N10XRP1` diagnostic checks metadata-prefix offsets, kernel/entry/end
offsets, seven mapping blocks and two kernel blocks. It reports computations with
`synthetic=1 materialized=0`. It never accesses the reserved window or invokes
serializers, metadata construction, MMIO, register, PM or transfer operations.

The new host harness injects reservation state and a planner stub to exercise only
wrapper guards, current-base propagation, failure reporting, plan-field rejection
and preparer negatives. It does not execute the production planner or a Linux
object and does not repeat the old v54 native/ABI/entry or PM suites. The targeted
component workflow separately compiles real pinned kernel headers in two clean,
isolated source/output trees. It records the exact archive digest, source hashes,
toolchain versions, commands, configuration, `.cmd` dependencies and object bytes;
symbol and wrapper call-relocation checks bind the actual integration.

The intended verdict is **actual-kernel object integration plus host-wrapper
evidence** after those checks pass. No full Image, BOOT, initramfs, phone cycle,
physical ownership, GIC handoff, DMA quiescence, XNU execution or deployment
readiness is claimed. All work and temporary outputs stay in project-private,
disjoint directories. Public workflow artifacts contain component proofs only.

On a Linux PC with the documented workflow toolchain, the new component command
is `python note10/device_test/build_xnu_runtime_plan_component.py --output
note10/private/xnu-runtime-plan-component`. It builds only `init.o` in each mode.
