"""Compile selected real XNU units using native Exynos-generated configurations.

Cache/page constants are explicitly synthetic. This is not a bootable kernel build.
"""
import hashlib
import json
import re
import shlex
import subprocess
import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from prepare_build_selection import ROOT
from build_windows_config import LLVM

UNITS = ('pexpert/arm/pe_note10_bootstrap.c', 'pexpert/arm/pe_note10_irq.c',
         'pexpert/arm/note10/gicv2.c', 'pexpert/arm/note10/gicv2_mmio.c', 'osfmk/arm/rtclock.c',
         'osfmk/arm64/machine_routines.c', 'osfmk/arm64/sleh.c', 'pexpert/arm/pe_identify_machine.c',
         'osfmk/arm/arm_init.c', 'osfmk/arm64/arm_vm_init.c')

# Public architecture implementations excluded by the current NOS_ARM/PPL
# selection. These are candidates for porting, not a complete platform archive.
PLATFORM_C = tuple('osfmk/arm/pmap/' + n + '.c' for n in
                   ('pmap', 'pmap_cs', 'pmap_data', 'pmap_iommu', 'pmap_misc', 'pmap_ppl_interface')) + \
             ('osfmk/arm/arm_init.c', 'osfmk/arm64/arm_vm_init.c', 'osfmk/arm64/pcb.c')
PLATFORM_ASM = tuple('osfmk/arm64/' + n + '.s' for n in
                     ('caches_asm', 'locore', 'cswitch', 'machine_routines_asm', 'start'))


def main():
    private = ROOT / 'note10/private/windows-xnu'
    configured = json.loads((private / 'configure-result.json').read_text())
    source = ROOT / configured['source_directory']
    for name, expected in configured.get('patched_source_sha256', {}).items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Patched source changed since configuration: ' + name)
    for item in configured['configured']:
        directory = private / 'configured' / item['variant'] / item['component']
        if hashlib.sha256((directory / 'Makefile').read_bytes()).hexdigest() != item['makefile_sha256']:
            raise ValueError('Native generated Makefile changed')
        for name, expected in item['headers'].items():
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
                raise ValueError('Native generated feature header changed')
    target = json.loads((ROOT / 'note10/target.json').read_text())
    compiler = os.environ.get('N10_CC') or str(LLVM / 'clang-23.exe')
    sdk = os.environ.get('N10_SDKROOT')
    mig = ROOT / target['research_directory'] / 'generated-headers-vmapple/RELEASE_ARM64_VMAPPLE'
    exported = private / 'exports'
    borrowed_mig = private / 'borrowed-mig'
    native_mig_report = private / 'native-mig-result.json'
    native_mig = None
    generated_mig = {}
    generated_extra = {}
    extra_report = private / 'native-extra-result.json'
    if sdk and extra_report.exists():
        for item in json.loads(extra_report.read_text())['generated_sources']:
            if not item['passed']:continue
            path = private / item['source']
            if not path.resolve().is_relative_to(private.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != item['source_sha256']:
                raise ValueError('Generated extra source escaped output or changed')
            generated_extra[(item['component'], item['selected_name'])] = path
    if sdk and native_mig_report.exists():
        candidate = json.loads(native_mig_report.read_text())
        if candidate['all_passed']:
            native_mig = private / 'native-mig'
            if hashlib.sha256((source / 'osfmk/mach/Makefile').read_bytes()).hexdigest() != candidate['source_makefile_sha256']:
                raise ValueError('Native MIG source Makefile changed')
            for item in candidate['interfaces']:
                header = native_mig / item['mode'] / 'osfmk/mach' / item['header']
                if hashlib.sha256(header.read_bytes()).hexdigest() != item['header_sha256']:
                    raise ValueError('Native MIG header changed')
            for item in candidate.get('generated_sources', []):
                if not item['passed']:continue
                generated_path = private / item['source']
                if not generated_path.resolve().is_relative_to(native_mig.resolve()):
                    raise ValueError('Generated MIG source path escaped output')
                if hashlib.sha256(generated_path.read_bytes()).hexdigest() != item['source_sha256']:
                    raise ValueError('Generated MIG source changed')
                generated_mig[item['selected_name']] = generated_path
    mig_hashes = {}
    for component in ('osfmk', 'bsd', 'iokit'):
        directory = mig / component / 'RELEASE'
        for header in directory.rglob('*.h'):
            relative = header.relative_to(directory)
            if len(relative.parts) < 2:
                continue  # Never borrow the foreign feature/configuration headers.
            path = borrowed_mig / component / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = header.read_bytes(); path.write_bytes(raw)
            mig_hashes[header.relative_to(mig).as_posix()] = hashlib.sha256(raw).hexdigest()
    exports = {'string.h': 'osfmk/libsa/string.h'}
    for name in ('kcov.h', 'kcov_data.h', 'kcov_ksancov.h', 'kcov_ksancov_data.h', 'kcov_stksz.h', 'kcov_stksz_data.h'):
        exports['san/' + name] = 'san/coverage/' + name
    for name in ('kasan.h', 'kasan-classic.h', 'kasan-tbi.h', 'ubsan_minimal.h', 'memintrinsics.h'):
        exports['san/' + name] = 'san/memory/' + name
    export_hashes = {}
    for name, original in exports.items():
        path = exported / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (source / original).read_bytes(); path.write_bytes(raw)
        export_hashes[original] = hashlib.sha256(raw).hexdigest()
    output = private / 'objects/DEVELOPMENT'
    output.mkdir(parents=True, exist_ok=True)
    results = []
    modes = {'--all-c': ('CFILES', 'C', 'all-c'), '--all-cxx': ('CXXFILES', 'C++', 'all-cxx'),
             '--all-asm': ('SFILES', 'assembly', 'all-asm'),
             '--platform-c': ('PLATFORM_C', 'C', 'platform-c'),
             '--platform-asm': ('PLATFORM_ASM', 'assembly', 'platform-asm')}
    mode = modes.get(sys.argv[1]) if len(sys.argv) == 2 else None
    audit = mode is not None
    skipped = []
    units = list(sys.argv[1:]) or list(UNITS)
    owners = {}
    input_files = {}
    if audit:
        units = []
        for component in ('osfmk', 'bsd', 'iokit', 'libkern', 'pexpert', 'libsa', 'security', 'san'):
            text = (private / 'configured/DEVELOPMENT' / component / 'Makefile').read_text().replace('\\\n', ' ')
            match = re.search(r'^' + mode[0] + r'=(.*)$', text, re.MULTILINE)
            for token in match.group(1).split() if match else []:
                if token.startswith('$(SOURCE_DIR)/'):
                    name = token[len('$(SOURCE_DIR)/'):]
                    if (source / name).is_file():
                        if name in owners and owners[name] != component:
                            raise ValueError('Source selected by multiple components: ' + name)
                        owners[name] = component
                        units.append(name)
                    else:skipped.append({'source': name, 'reason': 'selected source missing'})
                elif component == 'osfmk' and token in generated_mig:
                    name = '@generated/osfmk/' + token.removeprefix('./')
                    owners[name] = component
                    input_files[name] = generated_mig[token]
                    units.append(name)
                elif (component, token) in generated_extra:
                    name = '@generated/' + component + '/' + token.removeprefix('./')
                    owners[name] = component
                    input_files[name] = generated_extra[(component, token)]
                    units.append(name)
                else:skipped.append({'source': token, 'component': component, 'reason': 'generated source not yet built'})
        units = sorted(set(units))
        if mode[0].startswith('PLATFORM_'):
            units = list(PLATFORM_C if mode[0] == 'PLATFORM_C' else PLATFORM_ASM)
    private_flags = {
        'osfmk': ['-DMACH_KERNEL_PRIVATE', '-DMACH_KERNEL'],
        'bsd': ['-DDRIVER_PRIVATE', '-D_KERNEL_BUILD', '-DKERNEL_BUILD', '-DMACH_KERNEL', '-DBSD_BUILD', '-DBSD_KERNEL_PRIVATE'],
        'iokit': ['-DDRIVER_PRIVATE', '-DIOKIT_KERNEL_PRIVATE', '-DDRIVERKIT_PRIVATE=1', '-DIOMATCHDEBUG=1', '-DIOALLOCDEBUG=1', '-DPRIVATE_WIFI_ONLY=1', '-DIOASSERT=1'],
        'libkern': ['-DLIBKERN_KERNEL_PRIVATE', '-DOSALLOCDEBUG=1'],
        'pexpert': ['-DPEXPERT_KERNEL_PRIVATE'], 'libsa': ['-DLIBSA_KERNEL_PRIVATE'],
        'security': ['-DBSD_KERNEL_PRIVATE'], 'san': [],
    }
    def compile_one(name):
        original = input_files.get(name, source / name)
        if (name not in input_files and not original.resolve().is_relative_to(source.resolve())) or Path(name).suffix not in ('.c', '.cpp', '.cc', '.cxx', '.S', '.s'):
            raise ValueError('Invalid source input')
        # kperfbsd.c lives under osfmk/ but is selected by bsd/conf/files.
        component = owners.get(name, name.split('/')[0])
        config = private / 'configured/DEVELOPMENT' / component
        text = (config / 'Makefile').read_text()
        defines = re.search(r'^export CONFIG_DEFINES =(.*)$', text, re.MULTILINE).group(1)
        flags = shlex.split(defines)
        semantic_type_flags = []
        if name.startswith(('osfmk/vm/', 'bsd/vm/')) or name == 'bsd/kern/kern_mman.c':
            # These are the actual FORCE_UNSAFE_TYPES rules in the component
            # Makefile templates, not replacement typedefs or a safety opt-out.
            template = (source / component / 'conf/Makefile.template').read_text()
            if '$1_CFLAGS_ADD += -DVM_UNSAFE_TYPES' not in template:
                raise ValueError('Upstream semantic type rule changed')
            semantic_type_flags = ['-DVM_UNSAFE_TYPES=1']
        includes = [config, exported, source / 'EXTERNAL_HEADERS']
        if sdk and extra_report.exists():
            includes += [private / 'generated-extra' / c for c in (component, 'bsd', 'iokit')]
        if native_mig:
            if component == 'osfmk':includes.append(native_mig / 'kernel/osfmk')
            includes.append(native_mig / 'export/osfmk')
        includes.extend(private / 'source-exports' / c for c in
                        (component, *[c for c in ('osfmk', 'bsd', 'pexpert', 'libkern', 'iokit', 'libsa', 'security', 'san', 'EXTERNAL_HEADERS') if c != component]))
        includes.extend(private / 'configured/DEVELOPMENT' / c for c in
                        ('osfmk', 'bsd', 'iokit', 'libkern', 'pexpert', 'libsa', 'security', 'san') if c != component)
        includes.extend(source / c for c in ('osfmk', 'bsd', 'pexpert', 'libkern', 'libsa', 'iokit', 'security', 'san', '.'))
        if component == 'osfmk':
            includes.append(source / 'osfmk/libsa')  # Template's libsa include; keep BSD machine headers first.
            includes.append(source / 'EXTERNAL_HEADERS/corecrypto')
        includes.extend(borrowed_mig / c for c in ('osfmk', 'bsd', 'iokit'))
        includes.extend(mig / c for c in ('osfmk', 'bsd', 'iokit', 'libkern'))
        includes.extend(ROOT / 'host-tools/kdk/headers' / p for p in (
            'KDK_SDK.pkg/System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders/platform',
            'KDK.pkg/System/Library/KernelSupport'))
        if sdk:
            includes.append(ROOT / 'host-tools/opensource-declarations')
            includes.extend(Path(sdk) / p for p in (
                'System/Library/Frameworks/Kernel.framework/Versions/A/Headers',
                'System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders',
                'System/Library/Frameworks/Kernel.framework/Headers',
                'System/Library/Frameworks/Kernel.framework/PrivateHeaders',
                'usr/local/include', 'usr/include'))
        object_file = output / (name.replace('/', '_').replace('@', '') + '.o')
        command = [compiler, '--target=arm64-apple-darwin', '-march=armv8.2-a+crypto',
                   '-std=gnu11', '-O2', '-ffreestanding', '-fno-builtin', '-fno-common', '-fblocks',
                   '-nostdlibinc', '-fno-stack-protector', '-mno-implicit-float', '-mstrict-align',
                   '-ferror-limit=8', '-Darm64', '-DARM64', '-D__ARM64__', '-DLP64', '-DAPPLE', '-DKERNEL',
                   '-DKERNEL_PRIVATE', '-DXNU_KERNEL_PRIVATE', '-DPRIVATE', '-D__API__=v4',
                   '-DPAGE_SIZE_FIXED', '-DARM_LARGE_MEMORY=0', '-DVM_KERNEL_LINK_ADDRESS=0xfffffff007004000',
                   '-DCURRENT_MACHINE_CONFIG_LC=exynos9825',
                   '-DXNU_TARGET_OS_IOS', '-DXNU_PLATFORM_iPhoneOS', '-DARM64_BOARD_CONFIG_EXYNOS9825',
                   '-DN10_BOARD_SCHEMA=1', '-DN10_ICACHE_LINE_LOG2=6', '-DN10_DCACHE_LINE_LOG2=6',
                   '-DN10_MAX_CACHE_LINE_LOG2=7', '-DN10_KERNEL_PAGE_SHIFT=14',
                   '-include', str(config / 'meta_features.h'), *flags]
        if sdk:command.extend(['-isysroot', sdk])
        language = mode[1] if mode else 'C'
        if language == 'C++':
            command[command.index('-std=gnu11')] = '-std=gnu++2b'
            command += ['-fapple-kext', '-fsized-deallocation', '-nostdinc++']
        elif language == 'assembly':
            command.remove('-std=gnu11')
            command += ['-x', 'assembler-with-cpp', '-DASSEMBLER', '-D__ASSEMBLER__']
        command += ([] if language == 'assembly' else private_flags[component]) + semantic_type_flags
        if sdk:
            # Documented image4 kernel-build option: SDK availability macros
            # otherwise mix with the pinned public AvailabilityInternal.h.
            command.append('-DIMAGE4_STRIP_AVAILABILITY=1')
            if name in ('bsd/kern/subr_log.c', 'libkern/os/log.c'):
                command.append('-DOS_FIREHOSE_SPI=1')
        for directory in includes:
            command.extend(['-I', str(directory)])
        command.extend(['-c', str(original), '-o', str(object_file)])
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
        log = object_file.with_suffix('.log')
        log.write_bytes(result.stdout + result.stderr)
        passed = result.returncode == 0
        diagnostics = result.stderr.decode('utf-8', errors='replace')
        row = {'source': name, 'component': component, 'passed': passed, 'command': command,
                        'source_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
                        'object_sha256': hashlib.sha256(object_file.read_bytes()).hexdigest() if passed else None,
                        'diagnostics': diagnostics}
        if not audit:
            print(name + ': ' + ('compiled' if passed else 'blocked'), flush=True)
            if not passed:print(diagnostics[-6000:], flush=True)
        return row
    if audit:
        with ThreadPoolExecutor(max_workers=4) as pool:
            pending = [pool.submit(compile_one, name) for name in units]
            for future in as_completed(pending):
                results.append(future.result())
                if len(results) % 25 == 0:
                    print(str(len(results)) + '/' + str(len(units)) + ' ' + mode[1] + ' units checked; '
                          + str(sum(r['passed'] for r in results)) + ' compiled', flush=True)
        results.sort(key=lambda r: r['source'])
    else:
        results = [compile_one(name) for name in units]
    report = {'units': results, 'source_export_sha256': export_hashes,
              'borrowed_nested_generated_header_sha256': mig_hashes,
              'native_exynos_config': True, 'foreign_mig_version_headers': True, 'macos_kdk_declaration_headers': True,
              'native_mach_mig_headers': bool(native_mig),
              'synthetic_board_inputs': True, 'whole_kernel_build': False, 'device_operations': []}
    report['skipped_generated_sources'] = skipped
    report['architecture_candidates_not_selected_in_native_config'] = bool(mode and mode[0].startswith('PLATFORM_'))
    report['scope'] = (mode[1] if mode else 'C') + ' compiler audit with component-private flags; not a full Make build or per-file instrumentation reproduction'
    (output / (mode[2] + '-result.json' if audit else 'compile-result.json')).write_text(json.dumps(report, indent=2))
    print(json.dumps({'compiled': sum(r['passed'] for r in results), 'attempted': len(results),
                      'whole_kernel_build': False}))
    if not audit and not all(r['passed'] for r in results):raise SystemExit(1)


if __name__ == '__main__':
    main()
