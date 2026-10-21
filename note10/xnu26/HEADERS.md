# Actual XNU header dependency probe

The synthetic bootstrap/IRQ tests substitute kernel types, so they cannot detect all real-header
inclusion problems. A direct probe found one: both Note10 source units included `arm/cpu_topology.h`
before `machine/machine_routines.h`. The topology header explicitly requires inclusion through
machine routines, which defines `cluster_type_t` and `MAX_CPU_TYPES` first.

The Note10 units now include machine routines and omit the direct topology include. Patches 0003
and 0004 are regenerated from the corrected canonical units. No public reference source is edited.

## Inputs and isolation

- Public reference: Apple `xnu-12377.121.6`, commit `ac9718fb1af618d5ce8678d0dc6e8a58f252216f`.
- [Generated-header archive](https://github.com/blacktop/darwin-xnu-build/releases/tag/v26.5):
  `xnu-lib-26.5.tar.gz`, SHA256 `846e86ea2a2fca585e6b3e08548ab3fe0c3237a5df4e012089cf05b590c7cbc3`.
- Its version.c identifies `xnu-12377.121.6`; generated settings are **RELEASE ARM64 VMAPPLE**.
- Only 263 regular `.h` files are extracted; archive objects, executables and scripts are not used.
  Archive checksum, member paths and extracted-size limits are checked.
- `osfmk/libsa/string.h` is copied byte-for-byte to an isolated export root according to its Makefile.
  Adding all of `osfmk/libsa` to the include path would incorrectly shadow BSD `machine/types.h`.
- NDK Clang 9.0.8, `arm64-apple-darwin`, public source headers and generated configuration headers.
  No substitute kernel structs, disabled compiler errors or fabricated missing headers are used.

The VMAPPLE generated configuration is a foreign control input, not an Exynos board profile.
This is a header dependency probe, not compilation of a whole Note10 source unit or kernel.

## Regression and remaining failure

```powershell
python note10/xnu26/probe_kernel_headers.py
```

Three cases are checked:

| Case | Expected result |
|---|---|
| Old include order, VMAPPLE control | Fails with unknown `cluster_type_t` |
| Correct include order, VMAPPLE control | Header syntax passes |
| Correct include order, EXYNOS9825 | Fails at `arm64/proc_reg.h`: processor not supported |

The last failure is retained as evidence of the missing Exynos CPU/board profile. The probe does
not work around it by defining an Apple CPU or guessing cache/page geometry. Returning success from
the script means the regression expectations hold; **it does not mean Exynos headers compile**.

This probe intentionally keeps pristine board/proc headers as a regression baseline. Patch 0005
now provides a separate explicit-input board overlay; its real-header/component checks with synthetic
inputs are documented in [BOARD.md](BOARD.md). There is still no measured physical board profile.

Report, exact commands, compiler version, diagnostics and hashes are in
`note10/private/xnu26-header-probe/report.json`. The PC predevice runner includes this probe and
continues to report `deployment_ready=false`.
