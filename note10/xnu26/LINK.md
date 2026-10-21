# Experimental ARM64 kernel link

Verified run: [39560904016](https://github.com/eirblue/ios_note10p/actions/runs/39560904016), commit `ff5ace1`.

- Selected C 904/904, C++ 129/129, assembly 19/19, with no skipped generated inputs.
- Public architecture candidates: 10 C and 5 assembly units, all compiled.
- Real public kernel firehose: 1 unit; genuine version/section markers: 3 units.
- Native genassym: 149 constants, exactly matching the upstream sed recipe.
- All 1,071 objects passed an Apple `ld -r` merge.
- Six VM aliases came from real upstream export lists, not replacement functions.
- The plain arm64 slice of Apple's `libclang_rt.cc_kext_ios.a` supplied kernel compiler support.
- The subsequent static source-object link produced an arm64 `MH_EXECUTE`, 18,522,008 bytes.
- SHA256: `8584aec16c94eeb16b078cb18807f5b93b923c989c19afd78a778745d851454b`.
- No undefined symbols or dynamic-library load commands remained in the executable.

The relocatable merge still had 38 unresolved names, including linker-created section
boundaries and Mach-O image symbols. The final link resolved them. An entry routine
can become local after a merge; absence from `nm -g` does not establish its absence
from the executable. Final validation examines local symbols too.

## Scope and limits

`link_experimental_kernel.py` reads the real generic/ARM64 layout recipes from pinned
XNU `MakeInc.def`; its 53 base arguments were compared with GNU Make expansion.
This is an experimental source-object link, not a complete reproduction of upstream
Make, per-file instrumentation, KPI symbol sets or kernel collections.
The linker warns about prelink segments omitted from the original segment order and
moves `__LINKEDIT` last. Mac SDK declarations are used with an iOS deployment target.

The board page/cache parameters remain synthetic. Virtual linker addresses do not
supply a physical RAM/load/reserved-memory contract. A diagnostic archive of the 15
public architecture candidates was created and force-loaded in the final link; it is not verified Samsung hardware
support and does not establish DMA isolation, monitor services or sleep support.
No closed Apple platform support archive is linked as an Exynos replacement.

There is no Samsung boot image, verified handoff producer, real device boot,
storage/APFS/display/touch integration or native iOS userland/PAC integration.
Public XNU 12377.121.6 also differs from target IPSW XNU 12377.122.8.
Executable-link success does not establish bootability or userland ABI compatibility.
Only locally built experimental outputs and diagnostics may be retained by the manual
workflow; original firmware, IPSW, SDK/KDK contents and credentials remain excluded.

## Downloaded executable validation

The actual native-build artifact was downloaded to the Windows workspace.
`verify_experimental_artifact.py` verified its manifest hash, Mach-O bounds,
non-overlapping virtual segments, no writable executable segment, all six expected
architecture symbols and LC_UNIXTHREAD PC equal to `__start` at
`0xfffffff007340490`. No undefined symbol remained. Independent LLVM readobj
confirmed Mach-O arm64, ARM64_ALL subtype and MH_EXECUTE.
The downloaded 15-object archive also matched its recorded SHA256.

The manual workflow retains `note10-experimental-native-build` for seven days.
It contains source-built research outputs and a manifest, not a Samsung flash package.
Local copies remain under ignored `note10/private/cloud-runs/39560904016/`.
PC component verification separately passed all 28 checks with deployment_ready=false.
