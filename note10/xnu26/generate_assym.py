"""Generate ARM64 assembly offsets with the real XNU genassym.c and compiler.

Reuses the audited osfmk C environment, then follows upstream's -S and sed rule.
No hard-coded structure sizes or replacement kernel types are supplied.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from prepare_build_selection import ROOT


def main():
    private = ROOT / 'note10/private/windows-xnu'
    config = json.loads((private / 'configure-result.json').read_text())
    source = ROOT / config['source_directory']
    audit = json.loads((private / 'objects/DEVELOPMENT/all-c-result.json').read_text())
    unit = next(r for r in audit['units'] if r['source'] == 'osfmk/arm64/machine_routines.c')
    directory = private / 'configured/DEVELOPMENT/osfmk'
    assembly = directory / 'genassym.S'
    command = list(unit['command'])
    command[command.index('-c')] = '-S'
    command[command.index('-o') + 1] = str(assembly)
    command[command.index('-S') + 1] = str(source / 'osfmk/arm64/genassym.c')
    command.append('-fno-integrated-as')
    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
    (private / 'genassym.log').write_bytes(result.stdout + result.stderr)
    passed = result.returncode == 0
    constants = {}
    if passed:
        text = assembly.read_text()
        for name, prefix, number in re.findall(r'DEFINITION__define__([A-Za-z0-9_]+):\s*\.ascii\s+"([#$]*)(-?\d+)"', text):
            if name in constants:raise ValueError('Duplicate assembly offset: ' + name)
            constants[name] = (prefix, number)
        if len(constants) < 100:raise ValueError('Unexpected genassym assembly format/count')
        lines = []
        for name, (prefix, number) in constants.items():
            # Preserve the assembler immediate prefix, as the upstream sed does.
            prefix = prefix.lstrip('$')
            lines += ['#define ' + name + ' ' + prefix + number,
                      '#define ' + name + '_NUM ' + number]
        (directory / 'assym.s').write_text('\n'.join(lines) + '\n', newline='\n')
    report = {'passed': passed, 'constants': len(constants), 'command': command,
              'source_sha256': hashlib.sha256((source / 'osfmk/arm64/genassym.c').read_bytes()).hexdigest(),
              'synthetic_board_inputs': True, 'whole_kernel_build': False}
    (private / 'genassym-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'genassym_compiled': passed, 'constants': len(constants)}), flush=True)


if __name__ == '__main__':main()
