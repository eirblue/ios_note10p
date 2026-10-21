"""Compile genuine version and final section markers; no invented linker symbols."""
import hashlib
import json
from pathlib import Path
import subprocess
from prepare_build_selection import ROOT


def main():
    private = ROOT / 'note10/private/windows-xnu'
    configured = json.loads((private / 'configure-result.json').read_text())
    source = ROOT / configured['source_directory']
    metadata = json.loads((private / 'native-link/generate-result.json').read_text())
    if hashlib.sha256((private / 'native-link/version.c').read_bytes()).hexdigest() != metadata['version_c_sha256']:
        raise ValueError('Generated version source changed')
    audit = json.loads((private / 'objects/DEVELOPMENT/all-c-result.json').read_text())
    base = next(r for r in audit['units'] if r['source'] == 'osfmk/arm64/machine_routines.c')['command']
    units = []
    for name, path in (('@metadata/version.c', private / 'native-link/version.c'),
                       ('@metadata/lastkerneldataconst.c', source / 'libsa/lastkerneldataconst.c'),
                       ('@metadata/lastkernelconstructor.c', source / 'libsa/lastkernelconstructor.c')):
        command = list(base)
        obj = private / 'objects/DEVELOPMENT' / (name.replace('/', '_').replace('@','') + '.o')
        command[command.index('-c') + 1] = str(path)
        command[command.index('-o') + 1] = str(obj)
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
        (private / 'native-link' / (path.stem + '.log')).write_bytes(result.stdout + result.stderr)
        passed = result.returncode == 0
        units.append({'source': name, 'passed': passed, 'command': command,
                      'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                      'object_sha256': hashlib.sha256(obj.read_bytes()).hexdigest() if passed else None})
    report = {'units': units, 'whole_kernel_build': False, 'invented_absolute_symbols': False}
    (private / 'link-metadata-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'link_metadata_units_compiled': sum(r['passed'] for r in units), 'attempted': len(units)}), flush=True)
    if not all(r['passed'] for r in units):raise SystemExit(1)


if __name__ == '__main__':main()
