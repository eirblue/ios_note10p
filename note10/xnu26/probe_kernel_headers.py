"""Probe actual XNU header dependencies; no replacement kernel types or fake headers.

The pinned public VMAPPLE generated headers are a dependency diagnostic only.
They are never accepted as an Exynos kernel configuration.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import urllib.request
from prepare_build_selection import ROOT, NDK

URL = 'https://github.com/blacktop/darwin-xnu-build/releases/download/v26.5/xnu-lib-26.5.tar.gz'
SHA = '846e86ea2a2fca585e6b3e08548ab3fe0c3237a5df4e012089cf05b590c7cbc3'


def generated_headers(research):
    archive = research / 'xnu-lib-26.5.tar.gz'
    if not archive.exists():
        request = urllib.request.Request(URL, headers={'User-Agent': 'note10-port-research'})
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
        if hashlib.sha256(raw).hexdigest() != SHA:
            raise ValueError('Generated-header archive checksum mismatch')
        archive.write_bytes(raw)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA:
        raise ValueError('Local generated-header archive checksum mismatch')
    destination = research / 'generated-headers-vmapple'
    files = {}
    with tarfile.open(archive, 'r:gz') as package:
        version = package.extractfile('RELEASE_ARM64_VMAPPLE/version.c').read()
        if b'runner:xnu-12377.121.6"' not in version:
            raise ValueError('Generated-header source version mismatch')
        total = 0
        for member in package:
            if not member.isfile() or not member.name.endswith('.h'):
                continue  # Do not extract or execute any archive object/binary/script.
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or '..' in relative.parts or ':' in member.name or '\\' in member.name:
                raise ValueError('Unsafe archive member')
            total += member.size
            if total > 32 * 1024 * 1024:
                raise ValueError('Unexpected generated-header size')
            path = destination.joinpath(*relative.parts)
            if not path.resolve().is_relative_to(destination.resolve()):
                raise ValueError('Generated-header path escaped output')
            raw = package.extractfile(member).read()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            files[member.name] = hashlib.sha256(raw).hexdigest()
    return destination / 'RELEASE_ARM64_VMAPPLE', files


def context():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    research = (ROOT / target['research_directory']).resolve()
    if not research.is_relative_to(ROOT):
        raise ValueError('Research directory escapes repository')
    reference = json.loads((research / 'xnu-reference.json').read_text())
    if reference['commit'] != 'ac9718fb1af618d5ce8678d0dc6e8a58f252216f':
        raise ValueError('Reference differs from generated-header source')
    source = ROOT / reference['source_directory']
    generated, files = generated_headers(research)
    output = ROOT / 'note10/private/xnu26-header-probe'
    output.mkdir(exist_ok=True)
    # osfmk/libsa/Makefile exports string.h into the root. Adding the entire
    # directory to -I would incorrectly shadow BSD machine/types.h with libsa's.
    export_root = output / 'export-root'
    export_root.mkdir(exist_ok=True)
    string_header = (source / 'osfmk/libsa/string.h').read_bytes()
    (export_root / 'string.h').write_bytes(string_header)
    source_exports = {'osfmk/libsa/string.h': hashlib.sha256(string_header).hexdigest()}
    # san/coverage/Makefile exports these unmodified under the san include root.
    for name in ('kcov.h', 'kcov_data.h', 'kcov_ksancov.h', 'kcov_ksancov_data.h',
                 'kcov_stksz.h', 'kcov_stksz_data.h'):
        raw = (source / 'san/coverage' / name).read_bytes()
        destination = export_root / 'san' / name
        destination.parent.mkdir(exist_ok=True)
        destination.write_bytes(raw)
        source_exports['san/coverage/' + name] = hashlib.sha256(raw).hexdigest()
    tools = NDK / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    compiler = tools / 'clang.exe'
    includes = [generated / 'osfmk/RELEASE', generated / 'pexpert/RELEASE',
                generated / 'bsd/RELEASE', generated / 'libkern/RELEASE',
                generated / 'osfmk', generated / 'libkern', generated / 'bsd']
    includes.append(export_root)
    includes.extend(source / p for p in ('EXTERNAL_HEADERS', 'osfmk', 'bsd', 'pexpert',
                                        'libkern', 'libsa', 'iokit', 'security', 'san', '.'))
    common = ['--target=arm64-apple-darwin', '-march=armv8.2-a', '-ffreestanding',
              '-fno-builtin', '-fblocks', '-nostdlibinc', '-ferror-limit=8', '-fsyntax-only',
              '-Darm64', '-DARM64', '-D__ARM64__', '-DLP64', '-DAPPLE', '-DKERNEL',
              '-DKERNEL_PRIVATE', '-DXNU_KERNEL_PRIVATE', '-DPRIVATE', '-D__MACHO__=1']
    for path in includes:
        common.extend(['-I', str(path)])
    return reference, files, source_exports, compiler, common, output


def main():
    reference, files, source_exports, compiler, common, output = context()
    probe = output / 'headers.c'
    probe.write_text('#include <mach/vm_types.h>\n'
                     '#include <machine/machine_routines.h>\n#include <kern/debug.h>\n'
                     '#include <pexpert/pexpert.h>\n#include <pexpert/device_tree.h>\n', newline='\n')
    old_order = output / 'old-order.c'
    old_order.write_text('#include <mach/vm_types.h>\n#include <arm/cpu_topology.h>\n'
                         '#include <machine/machine_routines.h>\n', newline='\n')
    component_hashes = {}
    for name in ('pe_note10_irq.c', 'pe_note10_bootstrap.c'):
        component = ROOT / 'note10/xnu26' / name
        text = component.read_text(encoding='utf-8')
        if '#include <arm/cpu_topology.h>' in text or '#include <machine/machine_routines.h>' not in text:
            raise ValueError('Component bypasses the topology header inclusion contract: ' + name)
        component_hashes[name] = hashlib.sha256(component.read_bytes()).hexdigest()
    cases = []
    for name, board, unit in (('exynos9825', 'EXYNOS9825', probe),
                             ('vmapple', 'VMAPPLE', probe),
                             ('old-order-vmapple', 'VMAPPLE', old_order)):
        command = [str(compiler), *common, '-DARM64_BOARD_CONFIG_' + board, str(unit)]
        result = subprocess.run(command, capture_output=True, timeout=60)
        log = output / (name + '.log')
        log.write_bytes(result.stdout + result.stderr)
        diagnostics = result.stderr.decode('utf-8', errors='replace')
        cases.append({'name': name, 'board': board, 'syntax_passed': result.returncode == 0,
                      'command': command, 'diagnostics': diagnostics,
                      'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
    regression_passed = (not cases[0]['syntax_passed'] and 'processor not supported' in cases[0]['diagnostics']
                         and "unknown type name 'cluster_type_t'" not in cases[0]['diagnostics']
                         and cases[1]['syntax_passed'] and not cases[2]['syntax_passed']
                         and "unknown type name 'cluster_type_t'" in cases[2]['diagnostics'])
    report = {'source_commit': reference['commit'], 'archive_url': URL, 'archive_sha256': SHA,
              'component_sha256': component_hashes, 'include_order_regression_passed': regression_passed,
              'generated_header_sha256': files,
              'source_export_sha256': source_exports,
              'compiler_version': subprocess.check_output([str(compiler), '--version']).decode(),
              'cases': cases, 'replacement_kernel_types': False, 'whole_kernel_build': False,
              'exynos_config_ready': False,
              'limits': 'VMAPPLE RELEASE generated settings are foreign diagnostic inputs only. '
                        'No successful Exynos compile can be claimed with those settings.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'headers': len(files), 'cases': [{'name': c['name'], 'syntax_passed': c['syntax_passed']} for c in cases],
                      'include_order_regression_passed': regression_passed,
                      'report': 'note10/private/xnu26-header-probe/report.json'}))
    if not regression_passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
