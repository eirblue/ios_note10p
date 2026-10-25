# PC-only linked entry investigation

The actual source-built kernel from run 39560904016, SHA256
`8584aec16c94eeb16b078cb18807f5b93b923c989c19afd78a778745d851454b`,
was inspected and its initial entry executed in a synthetic model.
These checks do not execute the kernel on a phone or prove hardware compatibility.

## Real linked entry instructions

`test_linked_entry.py` loads the real Mach-O segments into synthetic physical RAM,
constructs boot arguments using the pinned ARM64 ABI, and starts at `__start`.
The boot argument memory offsets agree with locally generated native genassym
(`BA_VIRT_BASE=8`, `BA_PHYS_BASE=16`, `BA_MEM_SIZE=24`, `BA_BOOT_FLAGS=1136`).

Two synthetic RAM layouts each executed 24,957 real instructions and performed
8,250 stores / 66,000 bytes, stopping before the SCTLR_EL1 MMU-enable write.
The constructed TCR/TTBR tables were independently walked for the physical entry,
kernel virtual entry and both addresses of the boot arguments. All resolved as
expected. The boot argument buffer was unchanged and stores stayed inside the
modeled kernel allocation.
The four bootstrap table pages were prefilled with nonzero test bytes, so the
test also checks that initialization clears stale descriptors rather than relying
on Unicorn's initially zero-filled memory.

A negative case placed boot arguments elsewhere in otherwise modeled RAM. The
table validator correctly found that they were outside the kernel's initial
bootstrap mappings. It is not sufficient to choose any unused RAM address.
This compiled 16K configuration uses 32 MiB bootstrap blocks. Startup maps
multiple blocks from the block containing the image header; memory earlier than
that is excluded. The producer conservatively keeps metadata in the first block.
The sample addresses in the report are synthetic and must not be used as device
load addresses. An actual loader must reserve and validate placement explicitly.

System-register reads/writes and cache/TLB/barrier effects are modeled by hooks.
Synthetic CLIDR=0 is used; real cache maintenance is not exercised. No MMU-enable
instruction, C `arm_init`, driver, iOS process or physical CPU transition is tested.
Unicorn is a PC verification tool; the native iOS target is unchanged.

## Static instruction review

`audit_kernel_instructions.py` inspected 2,256,028 instruction/skip-data records.
No recognized PAuth instruction was reported. There were 19 apparent SVE/SME
candidates, 544 undecoded words or unmarked data records, and four accesses to an
implementation-defined system register. The image has no LC_DATA_IN_CODE table.
This is a candidate scan, not a complete ISA certification.

`review_instruction_candidates.py` matched all 19 vector candidates to exact source
data bytes: embedded panic strings, SHA256 K256 constants, LZ4 permutation data and
encoder literals. They are not evidence of executed SVE/SME code. Unknown records
remain unclassified rather than automatically accepted as CPU-compatible.

The four system-register sites belong to Apple's AWL WatchdogDiag0 support
(`S3_5_c15_c2_6`) in `osfmk/kern/debug.c`. Upstream defaults support to false and
enables it through `/arm-io/wdt` property `awl-scratch-supported`. An Exynos device
tree producer must not enable this Apple hardware path. The code remains in the
linked image; source gating does not constitute a Samsung watchdog driver.

## Reproduction

Requires Python, Capstone 5.0.9 and Unicorn 2.1.4, plus the saved native-build
artifact. Reports stay in ignored `note10/private/`.

```text
python note10/xnu26/audit_kernel_instructions.py PATH_TO_NATIVE_BUILD
python note10/xnu26/review_instruction_candidates.py
python note10/xnu26/test_linked_entry.py PATH_TO_NATIVE_BUILD
```

The review currently uses the saved run 39560904016 and pinned public XNU source.
It checks the executable hash before correlating findings.

Remaining PC work includes Exynos device-tree conversion, entry/handoff and
diagnostic-log implementation, and PAC
integration with XNU's loader/traps/process keys. Device observations are needed
to finalize actual RAM reservations, entry state and hardware ownership; they do
not prevent preparation and synthetic testing of these components.

The subsequent [boot contract work](BOOT-CONTRACT.md) supplies a bounded
boot-argument producer, explicit synthetic placement checker and raw ADT codec.
It compares actual C ABI bytes and executes the linked SecureDT functions.
The entry test now uses that producer and also walks every segment's endpoints.
Actual memory reservation, board DT conversion and CPU handoff remain unfinished.

The optional `--adapter ELF` path now starts with x0-x3 cleared and executes the
[post-shutdown entry adapter](../shim/TRANSFER.md) before the actual XNU entry.
Both synthetic RAM layouts execute 24,999 instructions through the same pre-MMU
stop, retaining the kernel table-store and segment-endpoint checks. This does
not run Linux shutdown/kexec or prove a usable handoff on the current recovery.

An optional [software VA continuation](POST-MMU-MODEL.md) now executes the linked
return to `_arm_init` and its first-call boundary. It validates copied aliases
against the generated tables, while leaving the MMU/cache/TLB transition modeled.
The default pre-MMU boundary and checks above remain unchanged.
