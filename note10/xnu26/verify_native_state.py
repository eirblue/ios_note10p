"""Check native preparation artifacts while reporting unresolved compiler/porting errors."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
from prepare_build_selection import ROOT
from build_windows_config import LLVM


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    private = ROOT / 'note10/private/windows-xnu'
    config = json.loads((private / 'configure-result.json').read_text())
    if len(config['configured']) != 24 or not config['native_config_executed']:
        raise ValueError('Native component configurations incomplete')
    for entry in config['configured']:
        directory = private / 'configured' / entry['variant'] / entry['component']
        if sha(directory / 'Makefile') != entry['makefile_sha256']:raise ValueError('Configured Makefile changed')
        for name, expected in entry['headers'].items():
            if sha(directory / name) != expected:raise ValueError('Configured feature header changed')
    exports = json.loads((private / 'exports-result.json').read_text())
    for name, info in exports['exported'].items():
        if sha(private / 'source-exports' / name) != info['sha256']:raise ValueError('Exported source header changed')
    selected = json.loads((private / 'objects/DEVELOPMENT/compile-result.json').read_text())
    source = ROOT / config['source_directory']
    if len(selected['units']) != 10 or not all(unit['passed'] for unit in selected['units']):
        raise ValueError('Selected real C units did not all compile')
    for unit in selected['units']:
        if sha(source / unit['source']) != unit['source_sha256']:raise ValueError('Compiled source changed')
        obj = private / 'objects/DEVELOPMENT' / (unit['source'].replace('/', '_') + '.o')
        if sha(obj) != unit['object_sha256']:raise ValueError('Compiled object changed')
    probe = 'int n10_summary = __has_builtin(__builtin_xnu_type_summary);\nint n10_compatible = __has_builtin(__builtin_xnu_types_compatible);\n'
    command = [str(LLVM / 'clang-23.exe'), '--target=arm64-apple-darwin', '-E', '-P', '-x', 'c', '-']
    result = subprocess.run(command, input=probe, capture_output=True, text=True, check=True)
    features = {name: bool(int(value)) for name, value in re.findall(r'int n10_(\w+) = (\d+);', result.stdout)}
    if set(features) != {'summary', 'compatible'}:raise ValueError('Compiler builtin probe output unexpected')
    audit = json.loads((private / 'objects/DEVELOPMENT/all-c-result.json').read_text())
    failures = Counter()
    for unit in audit['units']:
        if unit['passed']:continue
        match = re.search(r'(?:fatal )?error: (.*)', unit['diagnostics'])
        failures[(match.group(1) if match else 'nonzero exit').strip()] += 1
    report = {'native_configurations': len(config['configured']),
              'generated_feature_headers': sum(len(x['headers']) for x in config['configured']),
              'source_headers_exported': len(exports['exported']), 'selected_c_units_compiled': len(selected['units']),
              'c_audit': {'attempted': len(audit['units']), 'compiled': sum(x['passed'] for x in audit['units']),
                          'not_compiled_generated_sources': len(audit['skipped_generated_sources']),
                          'first_error_counts': dict(failures)},
              'llvm23_xnu_builtins': features, 'whole_kernel_build': False,
              'next_work': 'Inspect the designated repository macOS audit; complete platform support, remaining generated interfaces and whole-kernel link',
              'device_operations': []}
    (private / 'state-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ('native_configurations', 'generated_feature_headers', 'source_headers_exported',
                                          'selected_c_units_compiled', 'llvm23_xnu_builtins', 'whole_kernel_build')}))


if __name__ == '__main__':
    main()
