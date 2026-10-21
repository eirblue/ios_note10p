# Native configuration and Windows C compiler audit

No phone operations, complete kernel linkage or boot image are performed here. Physical cache/page
values remain unknown. All target compiles below use explicit synthetic board inputs.

## Host preparation

Portable LLVM-MinGW 20261006 (Clang 23.1.3) and WinFlexBison 2.5.25 are cached under `host-tools/windows-build`.
LLVM archive SHA256 matches the release asset digest. WinFlexBison's release API has no digest;
its observed SHA256 is recorded separately, without claiming independent publisher verification.
Nothing is installed system-wide. Compiler executables require execution permission in this sandbox.
PC verification dependencies are also cached in `host-tools/python-native-packages` (Unicorn 2.1.4,
Capstone 5.0.9, PyYAML 6.0.3, lz4 4.4.5, lzfse 0.4.2.post1). The predevice runner adds that cache
to child-process PYTHONPATH to avoid an access mismatch with the older package cache under elevation;
filesystem permissions and the system Python installation are not changed.

`build_windows_config.py` compiles the **actual public XNU SETUP/config program** as a Windows executable.
The original source is copied unchanged into isolation. A host-only compatibility header defines BSD
`u_char` as unsigned char and maps `index/rindex` to `strchr/strrchr`; it does not define target kernel types.
Flex/Bison generate the original lexer/parser, rather than replacing them with a Python config parser.

`configure_windows_xnu.py` copies the pinned public tree, applies all seven patches, and executes that
config program for RELEASE/DEVELOPMENT/DEBUG across eight components. It generates **24 Makefiles
and 421 feature-header instances**. Input/executable/patch/generated file hashes are recorded. The
pristine reference is preserved.

`export_source_headers.py` evaluates assignment/conditional fragments of source Makefiles with GNU
Make and copies **907 source exports** into their declared include layout. This resolves, for example,
`bsd/skywalk/channel/os_channel.h` → `skywalk/os_channel.h`. It is not a missing proprietary SDK header.
The helper does not execute the complete Make export stage; generated/missing inputs remain reported.

## Declaration dependencies

KDK 26.5 / build 25F71 was downloaded through ipsw's KDK catalog (Dortania mirror). Its published
SHA256 is `90ed319cd1ba6e23d1eefcee89fa1b10743f4cf60b85208ae52aa9f45543c7aa`.
The installer is **not executed**. `extract_kdk_headers.py` reads XAR entries, verifies their SHA1
checksums, streams PBZX/XZ and extracts only regular headers/plists from CPIO into the workspace.
The extracted platform declarations include TrustCache. These macOS declarations are not Exynos drivers
or proof of compatibility with the iOS target.

The initial 7-Zip XAR extraction produced incorrect duplicate member data. Those outputs are unused.
The custom XAR reader uses each TOC offset/length/checksum; resulting payload/header hashes are recorded
in `host-tools/kdk/headers-report.json`. The original DMG/PKG are retained.

Generated MIG/version headers from the pinned public macOS source bundle remain a labelled borrowed
input. Nested generated headers are separated from foreign feature/config headers; native feature
headers take precedence. MIG generation for the Exynos/iOS build is still incomplete.

## Compile results and limits

Ten entire C units compile with native Exynos-generated configurations: bootstrap, IRQ bridge, GIC
core/MMIO, rtclock, machine routines, sleh, machine identification, arm_init and arm_vm_init.
Patch 0007 excludes the unused Apple core-type helper header from Exynos sleh; Apple targets retain it.
Compiler arguments also include the reference iPhoneOS virtual link constant `0xfffffff007004000`.
This is not a measured physical load address or a device-ready memory contract.

The broader DEVELOPMENT C audit examined **863 existing C sources: 585 compiled, 278 failed** after
source exports were fixed. Another **40 selected generated C inputs were not yet generated**.
C++/assembly, per-file instrumentation reproduction and full Make/link are outside this audit.
Some compiled objects may represent conditionally empty units; counts do not establish subsystem operation.

The first reported errors in 257 failing units involve missing Apple-specific
`__builtin_xnu_type_summary` / `__builtin_xnu_types_compatible`. Other failures include platform/CPU
assumptions, incomplete generated interfaces, private declarations and differing sanitized VM types.
These failures have not been suppressed or replaced by constant-returning compiler/driver stubs.
Apple describes the type summary builtin's role in allocator checks in its
[XNU memory safety article](https://security.apple.com/blog/towards-the-next-generation-of-xnu-memory-safety/).

Reproduction after fetching the tool inputs:

```powershell
python note10/xnu26/build_windows_config.py
python note10/xnu26/configure_windows_xnu.py
python note10/xnu26/export_source_headers.py
python note10/xnu26/compile_native_components.py
python note10/xnu26/compile_native_components.py --all-c
```

Reports are under `note10/private/windows-config/` and `note10/private/windows-xnu/`.
No whole kernel or bootable package exists. The manual Apple-Clang cloud alternative is in [CLOUD.md](CLOUD.md).
