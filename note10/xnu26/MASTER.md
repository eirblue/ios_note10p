# Exynos MASTER and platform link inputs

Patch 0006 adds `config/MASTER.arm64.exynos9825` and changes the Exynos-specific platform archive
selection in `makedefs/MakeInc.def` after patch 0001. Other machine configurations retain the
existing KDK archive branch. This is source/config-text preparation, **not a linked kernel**.

## SoC configuration

The SoC MASTER is derived from pinned `MASTER.arm64.iPhoneOS` (SHA256
`b0b4913c03970ca793cd0d3fc319bce3fffef39b55ba2ecf1e6c430e2ce72f06`).
Upstream `doconf -soc exynos9825 -platform iPhoneOS` already searches the SoC-specific file before
the generic platform file. The existing component Makefiles also track the SoC-only filename as a
dependency. No changes to the generic Apple MASTER or `doconf` are required.

The profile removes unsupported Apple PPL, CPU counter/pervasive features and paravirtualized
ticket selection. SPTM/tag conditional groups become explicit empty groups. Other groups, including
MACF and kernel integrity, remain derived from the reference. This does not implement the missing
non-Apple pmap/security/CPU support or establish a working protection model.

Only iPhoneOS RELEASE/DEVELOPMENT/DEBUG builds are accepted by the new Make branch. KASAN/SPTM
configurations and other platforms stop with an error rather than inheriting this initial profile.

## Explicit platform support input

Exynos cannot use a nonexistent KDK `libEXYNOS9825.os.<config>.a`. The new branch requires
`N10_PLATFORM_ARCHIVE` explicitly; empty, missing, whitespace/comma-containing paths and non-`.a`
suffixes are rejected. An accepted path is passed to `-force_load`.

These are **path and selection checks**, not archive-content/architecture/symbol/ABI validation.
Passing a path does not prove it contains Exynos support. No complete platform archive has been
implemented, and the code does not substitute empty platform functions or silently omit this dependency.
The checks occur while MakeInc.def is parsed, so full build/setup currently also stops without an
explicit archive. A future platform archive/bootstrap build dependency cycle still needs resolution;
this patch does not supply a general bootstrap build mode.

## Validation

```powershell
python note10/xnu26/prepare_master_profile.py
python note10/xnu26/test_master_profile.py
python note10/xnu26/validate_series.py
```

- The generator applies patch 0001 in an isolated stage, checks its hash, applies/reverses 0006,
  then reverses 0001 and checks original bytes. Public source files are unchanged.
- Configuration text for RELEASE/DEVELOPMENT/DEBUG is produced by the **unchanged sed/awk pipeline
  extracted from pinned upstream doconf**. Git Bash runs only this selection stage, not the csh
  mutation/build stages. Both input MASTER files have no CPP conditional directives, so skipping
  `unifdef` here does not choose branches. Unknown/new conditionals stop the test.
- Selected options exclude PPL/SPTM/exclaves, CPU/pervasive counters and PV ticket; the monotonic
  pseudo-device is absent. MACH/BSD/MACF/kernel-integrity options remain selected. Assertions are
  absent in RELEASE and present in DEVELOPMENT/DEBUG.
- **17 GNU Make cases** exercise three accepted configurations, eleven rejected inputs and three
  existing machine branches. The accepted-path fixture is a real archive of one component object;
  it is only a path-check fixture and **is not complete platform support or a kernel-link test**.
- All six patches / 18 unique files apply/reverse in sequence without altering the reference.

Outputs: `note10/private/xnu26-master/`, including three `config.*_ARM64` text files and report hashes.
The native XNU `config` tool has not run. No generated component Makefiles/feature headers from this
profile, whole-kernel compile/link, boot image or hardware execution are claimed.
Existing real-header component checks still use the explicitly labelled foreign generated headers
described in [BOARD.md](BOARD.md). Darwin SDK/toolchain dependencies, physical profile values,
platform archive and runtime device integration remain unresolved.
