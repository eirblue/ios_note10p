# Same-boot RAM access diagnostic

The previous reservation-only device test passed. This opt-in Linux diagnostic
tests cached writes and reads within a newly reserved 256MiB window in the same
boot. It does not reuse the previous boot's physical address or branch to XNU.

The unchanged reservation source performs memblock exclusion and checks all
65,536 PFNs. The optional wrapper requires successful current reservation,
all valid/reserved pages, supported alignment/range and matching normal linear
mapping endpoints before calling the access core. A failed guard performs no
buffer reads or writes. There is no ADB-triggerable memory-write interface.

The core fills every 64-bit word with an index-dependent pattern, checks it,
repeats with the complemented pattern, then clears and checks the whole window.
The odd multiplicative index term gives distinct pattern values for distinct
indices. Volatile accesses and CPU memory barriers preserve the test operations;
periodic reschedule opportunities avoid a long unbroken process-context loop.
Any comparison failure causes the pattern phase to stop, followed by clearing
and zero verification. A failed test cannot produce a successful verdict.

For the complete window, a successful result requires:

- 33,554,432 words; 67,108,864 pattern writes and reads across two rounds.
- 33,554,432 zero stores and zero reads; zero mismatches; status zero.
- At least two intact distinct N10MEM1 records whose ID and geometry match the
  verified Image and same-boot N10RAM2 reservation evidence.

The complete record is printed 32 times with per-build ID, sequence, all counts
and FNV-1a damage detection. Damaged records are ignored, never repaired.
Checksummed failures, duplicate sequences, inconsistent geometry and incomplete
counts are rejected. The collector must not promote reservation-only evidence
to an access-test pass.

PC validation executes the actual core C on buffers through the full 256MiB
size, including read faults, dropped writes, address aliasing and invalid inputs.
The actual wrapper/checksum C is also executed with modeled kernel APIs. Eleven
failed reservation/mapping cases perform zero memory accesses; a compare failure
still runs clearing. These tests are not hardware memory tests.

```text
python note10/device_test/test_window_access_decode.py
python note10/device_test/test_window_access_core.py --output PRIVATE_NEW_CORE_DIRECTORY
python note10/device_test/test_window_access_gate.py --output PRIVATE_NEW_GATE_DIRECTORY
```

The Linux CI option is window_access=true; it implies caps/reserve. Existing
reservation-only builds remain unchanged when this option is absent. The
generated human-installed BOOT-only package explicitly identifies RAM writes.
It is paired with an original BOOT rollback and preserves recovery/DTB/DTBO/vbmeta.
Builders and collectors never install, reboot or write phone partitions.

This test uses Linux's active normal-memory mappings and caches. It does not
prove cache-off coherence, DMA/device quiescence, secondary-CPU shutdown, GIC
ownership, MMU transition, executable XNU entry, VM initialization or iOS boot.
Its physical addresses are historical evidence after reboot, not live recovery
RAM authorization. The installed access kernel still requires a separate manual
device test; a successful source build or PC test does not establish that result.

## Experimental XNU data-stage extension

The optional `--xnu-payload` build mode extends this diagnostic after the cached
RAM pattern test. It reads a bounded `kernel.mem` from the built-in initramfs,
checks its build-bound SHA-256, zeroes the current boot's reserved window, copies
the data-only experimental XNU memory image there, and compares a second SHA-256
readback. It verifies that the unused tail remains zero. A failure after copying
scrubs the reserved window. Complete results are emitted as checksummed N10XNU1
records and must match the payload size/hash from the exact Linux Image and paired
manual package.

This is a RAM staging diagnostic only. The currently available source-built Mach-O
is experimental and does not represent a complete upstream XNU build. Its bytes
are never branched to or interpreted on the phone. The diagnostic does not create
boot_args or a device-specific ADT and does not stop Linux CPUs/devices or transfer
cache, MMU, timer, or GIC ownership. It cannot establish that XNU can boot.

Build workflow: set `window_access=true`, `xnu_stage=true`, and select the
successful artifact run containing `note10-experimental-native-build`. The
workflow downloads that artifact, validates its Mach-O manifest, produces a
relocatable memory image, builds the pinned Linux source, and emits a research-only
artifact. A separate local packaging step is still required to pair the Image
with this device's private backup and create a BOOT-only manual test/rollback ZIP.
No workflow step installs, reboots, flashes, or executes XNU on the phone.

## Logs containing several boots

The collector preserves the full raw log. If intact zero-time Linux boot banners
are present, it requires the last banner to match the exact verified Image banner
and selects the contiguous suffix beginning there. Selection offsets and SHA256
are recorded alongside the raw hash. It never searches older boots for a passing
result. With no intact boundary, it applies the existing strict decoders to the
whole input. Duplicate sequences within the selected input remain an error, and
evidence families cannot be assembled from different boot intervals. Corrupted
characters are not repaired.
