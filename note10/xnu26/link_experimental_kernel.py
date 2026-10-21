"""Try a static research Mach-O link using real upstream ARM64 layout options.

This diagnostic never packages or uploads the binary and has no device access.
Source compilation is audited separately; a failed link remains a failed link.
"""
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys
from prepare_build_selection import ROOT


def layout_flags(text):
    """Read only unconditional base recipes; do not emulate the full XNU Make."""
    joined = text.replace('\\\n', ' ')
    variables = {}
    for name in ('ARM64_PLKSEG_ADDR', 'ARM64_LINK_ADDR', 'LDFLAGS_KERNEL_GEN',
                 'LDFLAGS_KERNEL_GENARM64', 'LDFLAGS_KERNEL_SEGARM64_SEG_ORDER',
                 'LDFLAGS_KERNEL_SEGARM64'):
        matches = re.findall(r'^' + name + r'\s*=\s*([^\n]*)', joined, re.M)
        if not matches:raise ValueError('Missing upstream linker recipe: ' + name)
        # First ARM64 addresses are iPhoneOS small-memory defaults; later
        # assignments belong to the MacOSX conditional, which is not selected.
        if len(matches) != 1 and not name.startswith('ARM64_'):
            raise ValueError('Ambiguous upstream linker recipe: ' + name)
        variables[name] = matches[0].strip()
    recipe = ' '.join(variables[n] for n in
        ('LDFLAGS_KERNEL_GEN', 'LDFLAGS_KERNEL_GENARM64', 'LDFLAGS_KERNEL_SEGARM64'))
    for _ in range(3):
        recipe = re.sub(r'\$\((\w+)\)', lambda m: variables[m[1]], recipe)
    if '$' in recipe:raise ValueError('Unexpanded linker recipe')
    return shlex.split(recipe), variables


def main():
    if sys.platform != 'darwin':raise SystemExit('Experimental native link requires macOS')
    private = ROOT / 'note10/private/windows-xnu'
    inputs = json.loads((private / 'link-audit-result.json').read_text())
    report = {'attempted': False, 'whole_kernel_linked': False,
              'deployment_ready': False, 'boot_image_created': False, 'device_operations': [],
              'scope': 'Experimental source-object link; not a full upstream Make build',
              'synthetic_board_inputs': True, 'symbolsets_for_kext_loading_supplied': False}
    if inputs['compile_failures'] or not inputs['relocatable_merge_passed']:
        report['blocked_by'] = 'Incomplete source objects or failed relocatable merge'
    else:
        config = json.loads((private / 'configure-result.json').read_text())
        source = ROOT / config['source_directory']
        definition = source / 'makedefs/MakeInc.def'
        flags, variables = layout_flags(definition.read_text())
        tools = json.loads((ROOT / 'note10/private/cloud-toolchain-result.json').read_text())
        output = private / 'note10-experimental.macho'
        filelist = private / 'source-objects.filelist'
        platform = json.loads((private / 'platform-archive-result.json').read_text())
        platform_flags = []
        if platform['archive_created']:
            archive = private / 'libNote10.architecture-candidates.a'
            if hashlib.sha256(archive.read_bytes()).hexdigest() != platform['archive_sha256']:
                raise ValueError('Architecture archive changed after creation')
            excluded = {s.replace('/', '_') + '.o' for s in platform['objects']}
            selected = [p for p in filelist.read_text().splitlines() if Path(p).name not in excluded]
            if len(selected) + len(excluded) != len(filelist.read_text().splitlines()):
                raise ValueError('Architecture archive replacement did not match source object set')
            filelist = private / 'kernel-selected-objects.filelist'
            filelist.write_text('\n'.join(selected) + '\n')
            platform_flags = ['-rdynamic', '-Wl,-force_load,' + str(archive)]
        command = [tools['compiler'], '--target=arm64-apple-ios26.5.2',
                   '-mcpu=generic', '-march=armv8.2-a+crypto', '-isysroot', tools['sdk'],
                   *flags, *platform_flags, '-Wl,-filelist,' + str(filelist),
                   '-Wl,-alias_list,' + str(private / 'selected-aliases.exp')]
        runtime = inputs['compiler_kernel_runtime']
        if runtime['selected']:command.append(runtime['file'])
        command += ['-o', str(output)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        (private / 'kernel-link.log').write_text(result.stdout + result.stderr)
        report.update({'attempted': True, 'command': command, 'returncode': result.returncode,
                       'architecture_candidate_archive_supplied': platform['archive_created'],
                       'upstream_layout_sha256': hashlib.sha256(definition.read_bytes()).hexdigest(),
                       'layout_variables': variables,
                       'virtual_addresses_are_physical_load_contract': False})
        if result.returncode == 0:
            raw = output.read_bytes()
            magic, cpu, subtype, kind, count, size, header_flags, reserved = struct.unpack_from('<8I', raw)
            if magic != 0xfeedfacf or cpu != 0x100000c or subtype != 0 or kind != 2:
                raise ValueError('Link output is not a plain arm64 MH_EXECUTE')
            offset = 32; dynamic = []; segments = []
            for _ in range(count):
                cmd, length = struct.unpack_from('<II', raw, offset)
                if length < 8 or offset + length > 32 + size:raise ValueError('Invalid Mach-O load command')
                if cmd in (0xc, 0x18 | 0x80000000, 0x1f | 0x80000000):dynamic.append(cmd)
                if cmd == 0x19:segments.append(raw[offset+8:offset+24].split(b'\0')[0].decode())
                offset += length
            nm = subprocess.run(['xcrun', 'nm', '-u', str(output)], capture_output=True, text=True, check=True)
            (private / 'kernel-undefined.log').write_text(nm.stdout + nm.stderr)
            all_symbols = subprocess.check_output(['xcrun', 'nm', str(output)], text=True)
            (private / 'kernel-symbols.log').write_text(all_symbols)
            present = {line.split()[-1] for line in all_symbols.splitlines() if line.split()}
            entries = {n: n in present for n in ('__start', '_start_first_cpu', '_arm_init',
                        '_arm_vm_init', '_pmap_bootstrap', '_PE_init_platform')}
            report.update({'whole_kernel_linked': not dynamic and not nm.stdout.strip(),
                           'mach_o_type': 'MH_EXECUTE', 'architecture': 'arm64',
                           'dynamic_library_load_commands': dynamic, 'segments': segments,
                           'undefined_symbol_output': nm.stdout,
                           'entry_architecture_symbols_present': entries,
                           'output_sha256': hashlib.sha256(raw).hexdigest(), 'output_size': len(raw)})
            if not all(entries.values()):raise ValueError('Expected architecture entry symbols absent from executable')
            if report['whole_kernel_linked']:
                exported = ROOT / 'note10/private/native-built-artifacts'
                exported.mkdir(exist_ok=True)
                shutil.copyfile(output, exported / output.name)
                if platform['archive_created']:
                    shutil.copyfile(archive, exported / archive.name)
                (exported / 'build-manifest.json').write_text(json.dumps(report, indent=2))
    (private / 'kernel-link-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ('attempted', 'whole_kernel_linked', 'deployment_ready')}), flush=True)


if __name__ == '__main__':main()
