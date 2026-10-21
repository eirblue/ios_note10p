"""Archive verified public architecture objects, without claiming hardware readiness."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from prepare_build_selection import ROOT


def main():
    if sys.platform != 'darwin':raise SystemExit('Native platform archive requires macOS')
    private = ROOT / 'note10/private/windows-xnu'
    objects = private / 'objects/DEVELOPMENT'
    units = []
    for name in ('platform-c-result.json', 'platform-asm-result.json'):
        units += json.loads((objects / name).read_text())['units']
    report = {'archive_created': False, 'hardware_verified': False,
              'production_platform_complete': False, 'synthetic_board_inputs': True,
              'device_operations': []}
    if not units or not all(u['passed'] for u in units):
        report['blocked_by'] = 'Architecture candidate compilation incomplete'
    else:
        paths = []
        for unit in units:
            p = objects / (unit['source'].replace('/', '_').replace('@', '') + '.o')
            if hashlib.sha256(p.read_bytes()).hexdigest() != unit['object_sha256']:
                raise ValueError('Architecture object changed: ' + unit['source'])
            paths.append(p)
        if len(paths) != len(set(paths)):raise ValueError('Duplicate architecture object')
        filelist = private / 'platform-objects.filelist'
        filelist.write_text('\n'.join(str(p) for p in paths) + '\n')
        archive = private / 'libNote10.architecture-candidates.a'
        result = subprocess.run(['xcrun', 'libtool', '-static', '-arch_only', 'arm64',
                                 '-filelist', str(filelist), '-o', str(archive)],
                                capture_output=True, text=True, timeout=120)
        (private / 'platform-archive.log').write_text(result.stdout + result.stderr)
        if result.returncode == 0:
            arch = subprocess.check_output(['xcrun', 'lipo', '-archs', str(archive)], text=True).split()
            if arch != ['arm64']:raise ValueError('Unexpected platform archive architecture')
            report.update({'archive_created': True, 'architectures': arch,
                           'objects': {u['source']: u['object_sha256'] for u in units},
                           'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
        else:report.update({'blocked_by': 'Native archiver failed', 'returncode': result.returncode})
    (private / 'platform-archive-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ('archive_created', 'production_platform_complete')}), flush=True)


if __name__ == '__main__':main()
