"""Audit compiled object symbol closure and try a relocatable merge on macOS.

The merge stays MH_OBJECT: no kernel layout, platform archive, entry, boot image,
or device operation is supplied. Undefined and weak imports remain diagnostics.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from prepare_build_selection import ROOT


def symbols(text):
    defined = defaultdict(list); references = defaultdict(list); current = ''
    for line in text.splitlines():
        if line.endswith('.o:'):
            current = line[:-1];continue
        match = re.match(r'^\s*(?:[0-9A-Fa-f]+\s+)?([A-Za-z?])\s+(\S+)', line)
        if not match:continue
        kind, symbol = match.groups()
        (references if kind.upper() == 'U' else defined)[symbol].append(current)
    return defined, references


def main():
    if sys.platform != 'darwin':raise SystemExit('Native link input audit requires macOS')
    private = ROOT / 'note10/private/windows-xnu'
    objects = private / 'objects/DEVELOPMENT'
    paths = []; skipped = []; failed = 0
    reports = [objects / n for n in ('all-c-result.json', 'all-cxx-result.json', 'all-asm-result.json')]
    for name in ('platform-c-result.json', 'platform-asm-result.json'):
        if (objects / name).exists():reports.append(objects / name)
    optional = private / 'public-dependencies-result.json'
    if optional.exists():reports.append(optional)
    optional = private / 'link-metadata-result.json'
    if optional.exists():reports.append(optional)
    groups = {}
    for report_path in reports:
        report = json.loads(report_path.read_text())
        group = 'selected' if report_path.name.startswith('all-') else 'architecture_candidates' if report_path.name.startswith('platform-') else 'link_metadata' if report_path.name.startswith('link-metadata') else 'public_dependency_candidates'
        counts = groups.setdefault(group, {'compiled': 0, 'failed': 0})
        skipped += report.get('skipped_generated_sources', [])
        for unit in report['units']:
            if not unit['passed']:failed += 1;counts['failed'] += 1;continue
            path = objects / (unit['source'].replace('/', '_').replace('@', '') + '.o')
            if hashlib.sha256(path.read_bytes()).hexdigest() != unit['object_sha256']:
                raise ValueError('Object changed after compilation: ' + path.name)
            paths.append(path)
            counts['compiled'] += 1
    if len(paths) != len(set(paths)):raise ValueError('Duplicate object input')
    nm = subprocess.check_output(['xcrun', '-f', 'nm']).decode().strip()
    result = subprocess.run([nm, '-g', *[p.name for p in paths]], cwd=objects,
                            capture_output=True, text=True, timeout=90, check=True)
    (private / 'symbol-audit.log').write_text(result.stdout + result.stderr)
    defined, references = symbols(result.stdout)
    unresolved = {n: sorted(set(v)) for n, v in references.items() if n not in defined}
    before_aliases = len(unresolved)
    entry_names = ('__start', '_start_first_cpu', '_arm_init', '_arm_vm_init', '_pmap_bootstrap', '_PE_init_platform')
    entry_inputs = {n: n in defined for n in entry_names}
    configured = json.loads((private / 'configure-result.json').read_text())
    source = ROOT / configured['source_directory']
    aliases = {}; alias_inputs = []; alias_provenance = {}
    # These are the real generic/ARM64 export aliases. Only materialize aliases
    # actually referenced by this object set with a present implementation.
    for path in sorted((source / 'config').glob('*.exports')):
        if not re.fullmatch(r'[^.]+(?:\.arm64)?\.exports', path.name):continue
        for line in path.read_text().splitlines():
            entry = line.split('#', 1)[0].strip()
            if entry.count(':') != 1:continue
            alias, implementation = [s.strip() for s in entry.split(':')]
            if not all(re.fullmatch(r'[_A-Za-z][_A-Za-z0-9$]*', s) for s in (alias, implementation)):continue
            if alias not in unresolved or implementation not in defined:continue
            if alias in aliases and aliases[alias] != implementation:raise ValueError('Ambiguous kernel alias')
            aliases[alias] = implementation
            alias_inputs.append(alias + ':' + implementation)
            alias_provenance[path.relative_to(source).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    alias_input = private / 'selected-aliases.exports'
    alias_file = private / 'selected-aliases.exp'
    alias_input.write_text('\n'.join(sorted(set(alias_inputs))) + '\n')
    subprocess.run(['/bin/sh', str(source / 'config/generate_linker_aliases.sh'),
                    str(alias_file), str(alias_input)], check=True)
    filelist = private / 'source-objects.filelist'
    filelist.write_text('\n'.join(str(p) for p in paths) + '\n')
    partial = private / 'note10-source-partial.o'
    ld = subprocess.check_output(['xcrun', '-f', 'ld']).decode().strip()
    command = [ld, '-r', '-arch', 'arm64', '-o', str(partial), '-filelist', str(filelist)]
    if aliases:command += ['-alias_list', str(alias_file)]
    toolchain = json.loads((ROOT / 'note10/private/cloud-toolchain-result.json').read_text())
    runtime = Path(toolchain['compiler_runtime_directory']) / 'lib/darwin/libclang_rt.cc_kext_ios.a'
    runtime_info = {'selected': False, 'required_kind': 'iOS kernel compiler runtime, plain arm64'}
    if runtime.is_file():
        arch = subprocess.run(['xcrun', 'lipo', '-archs', str(runtime)], capture_output=True, text=True, check=True).stdout.split()
        runtime_info.update({'file': str(runtime), 'architectures': arch,
                             'sha256': hashlib.sha256(runtime.read_bytes()).hexdigest()})
        if 'arm64' in arch:
            command.append(str(runtime));runtime_info['selected'] = True
    linked = subprocess.run(command, capture_output=True, text=True, timeout=120)
    (private / 'link-audit.log').write_text(linked.stdout + linked.stderr)
    if linked.returncode == 0:
        check = subprocess.check_output([nm, '-g', str(partial)], text=True)
        merged_defined, merged_references = symbols(check)
        for alias in aliases:
            if alias not in merged_defined:
                raise ValueError('Requested native alias was not defined by linker: ' + alias)
        unresolved = {n: sorted(set(references.get(n, ['compiler runtime / merged object'])))
                      for n in merged_references if n not in merged_defined}
        defined = merged_defined
    report = {'compiled_objects': len(paths), 'compile_failures': failed,
              'input_groups': groups,
              'upstream_aliases_resolved': aliases if linked.returncode == 0 else {},
              'upstream_alias_source_sha256': alias_provenance,
              'compiler_kernel_runtime': runtime_info,
              'unresolved_names_before_aliases': before_aliases,
              'skipped_generated_inputs': skipped, 'defined_external_symbols': len(defined),
              'unresolved_external_symbols': unresolved,
              'unresolved_note': 'Includes weak/optional imports; absence from this partial set is not an ABI proof.',
              'entry_architecture_symbols_in_input_objects': entry_inputs,
              'entry_architecture_symbols_external_after_merge': {n: n in defined for n in entry_names},
              'relocatable_merge_passed': linked.returncode == 0, 'merge_command': command,
              'partial_object_sha256': hashlib.sha256(partial.read_bytes()).hexdigest() if linked.returncode == 0 else None,
              'whole_kernel_linked': False, 'platform_archive_supplied': False,
              'boot_image_created': False, 'device_operations': []}
    (private / 'link-audit-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ('compiled_objects', 'compile_failures',
                      'entry_architecture_symbols_in_input_objects', 'relocatable_merge_passed', 'whole_kernel_linked')}), flush=True)
    print('Unresolved external symbol names: ' + str(len(unresolved)), flush=True)


if __name__ == '__main__':main()
