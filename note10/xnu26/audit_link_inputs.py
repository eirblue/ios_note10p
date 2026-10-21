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


def main():
    if sys.platform != 'darwin':raise SystemExit('Native link input audit requires macOS')
    private = ROOT / 'note10/private/windows-xnu'
    objects = private / 'objects/DEVELOPMENT'
    paths = []; skipped = []; failed = 0
    for name in ('all-c-result.json', 'all-cxx-result.json', 'all-asm-result.json'):
        report = json.loads((objects / name).read_text())
        skipped += report.get('skipped_generated_sources', [])
        for unit in report['units']:
            if not unit['passed']:failed += 1;continue
            path = objects / (unit['source'].replace('/', '_').replace('@', '') + '.o')
            if hashlib.sha256(path.read_bytes()).hexdigest() != unit['object_sha256']:
                raise ValueError('Object changed after compilation: ' + path.name)
            paths.append(path)
    if len(paths) != len(set(paths)):raise ValueError('Duplicate object input')
    nm = subprocess.check_output(['xcrun', '-f', 'nm']).decode().strip()
    result = subprocess.run([nm, '-g', *[p.name for p in paths]], cwd=objects,
                            capture_output=True, text=True, timeout=90, check=True)
    (private / 'symbol-audit.log').write_text(result.stdout + result.stderr)
    defined = defaultdict(list); references = defaultdict(list); current = ''
    for line in result.stdout.splitlines():
        if line.endswith('.o:'):
            current = line[:-1];continue
        match = re.match(r'^\s*(?:[0-9A-Fa-f]+\s+)?([A-Za-z?])\s+(\S+)', line)
        if not match:continue
        kind, symbol = match.groups()
        (references if kind.upper() == 'U' else defined)[symbol].append(current)
    unresolved = {n: sorted(set(v)) for n, v in references.items() if n not in defined}
    filelist = private / 'source-objects.filelist'
    filelist.write_text('\n'.join(str(p) for p in paths) + '\n')
    partial = private / 'note10-source-partial.o'
    ld = subprocess.check_output(['xcrun', '-f', 'ld']).decode().strip()
    command = [ld, '-r', '-arch', 'arm64', '-o', str(partial), '-filelist', str(filelist)]
    linked = subprocess.run(command, capture_output=True, text=True, timeout=120)
    (private / 'link-audit.log').write_text(linked.stdout + linked.stderr)
    report = {'compiled_objects': len(paths), 'compile_failures': failed,
              'skipped_generated_inputs': skipped, 'defined_external_symbols': len(defined),
              'unresolved_external_symbols': unresolved,
              'unresolved_note': 'Includes weak/optional imports; absence from this partial set is not an ABI proof.',
              'entry_architecture_symbols_present': {n: n in defined for n in
                  ('_start', '_arm_init', '_arm_vm_init', '_pmap_bootstrap', '_PE_init_platform')},
              'relocatable_merge_passed': linked.returncode == 0, 'merge_command': command,
              'partial_object_sha256': hashlib.sha256(partial.read_bytes()).hexdigest() if linked.returncode == 0 else None,
              'whole_kernel_linked': False, 'platform_archive_supplied': False,
              'boot_image_created': False, 'device_operations': []}
    (private / 'link-audit-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ('compiled_objects', 'compile_failures',
                      'entry_architecture_symbols_present', 'relocatable_merge_passed', 'whole_kernel_linked')}), flush=True)
    print('Unresolved external symbol names: ' + str(len(unresolved)), flush=True)


if __name__ == '__main__':main()
