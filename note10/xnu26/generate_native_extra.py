"""Generate selected BSD and IIG inputs using real upstream tools on macOS."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from prepare_build_selection import ROOT


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if sys.platform != 'darwin':raise SystemExit('Native extra generators require macOS')
    private = ROOT / 'note10/private/windows-xnu'
    config = json.loads((private / 'configure-result.json').read_text())
    source = ROOT / config['source_directory']
    base = private / 'generated-extra'; base.mkdir(parents=True, exist_ok=True)
    rows = []; commands = []
    def run(command, cwd, name):
        result = subprocess.run(command, cwd=cwd, capture_output=True, timeout=60)
        (base / (name + '.log')).write_bytes(result.stdout + result.stderr)
        commands.append({'command': command, 'exit_code': result.returncode})
        return result
    def record(component, token, path, definition=None):
        rows.append({'component': component, 'selected_name': token,
                     'source': path.relative_to(private).as_posix(), 'passed': path.is_file(),
                     'source_sha256': sha(path) if path.is_file() else None,
                     'definition_sha256': sha(definition) if definition else None})
    bsd = base / 'bsd'; bsd.mkdir(exist_ok=True)
    master_source = source / 'bsd/kern/syscalls.master'
    # Upstream MakeInc.rule runs unifdef with SEED_DEFINES. This standalone
    # public configuration supplies no private seed definitions.
    unifdef = subprocess.check_output(['xcrun', '-f', 'unifdef']).decode().strip()
    result = run([unifdef, str(master_source)], bsd, 'syscalls-master')
    if result.returncode not in (0, 1):raise ValueError('Syscall master unifdef failed')
    master = bsd / 'bsd.syscalls.master'; master.write_bytes(result.stdout)
    makesyscalls = source / 'bsd/kern/makesyscalls.sh'
    for mode in ('proto', 'header', 'table', 'names', 'systrace'):
        result = run(['/bin/sh', str(makesyscalls), str(master), mode], bsd, 'syscalls-' + mode)
        if result.returncode:raise ValueError('Upstream syscall generator failed: ' + mode)
    (bsd / 'sys').mkdir(exist_ok=True)
    for name in ('sysproto.h', 'syscall.h'):shutil.copyfile(bsd / name, bsd / 'sys' / name)
    for name in ('init_sysent.c', 'syscalls.c', 'systrace_args.c'):
        record('bsd', './' + name, bsd / name, master_source)
    record('bsd', './ioconf.c', private / 'configured/DEVELOPMENT/bsd/ioconf.c')
    result = subprocess.run(['xcrun', '-f', 'iig'], capture_output=True, text=True)
    iig = result.stdout.strip() if result.returncode == 0 else None
    if iig:
        flags = ['-I' + str(source / c) for c in ('iokit', 'osfmk', 'bsd')]
        flags += ['-I' + str(bsd), '-I' + str(source / 'EXTERNAL_HEADERS'),
                  '-isysroot', os.environ['N10_SDKROOT'], '-x', 'c++', '-std=gnu++2b',
                  '-D__IIG=1', '-DDRIVERKIT_PRIVATE=1', '-DPRIVATE_WIFI_ONLY=1']
        text = (private / 'configured/DEVELOPMENT/iokit/Makefile').read_text().replace('\\\n', ' ')
        selected = re.search(r'^CXXFILES=(.*)$', text, re.M).group(1).split()
        for token in selected:
            if not token.startswith('./') or not token.endswith('.iig.cpp'):continue
            relative = Path(token.removeprefix('./'))
            definition = source / 'iokit' / relative.with_suffix('')
            impl = base / 'iokit' / relative; impl.parent.mkdir(parents=True, exist_ok=True)
            header = impl.with_name(impl.name.removesuffix('.iig.cpp') + '.h')
            options = ['--framework-name', 'DriverKit'] if relative.parts[0] == 'DriverKit' else []
            result = run([iig, '--def', str(definition), '--header', str(header), '--impl', str(impl),
                          *options, '--', *flags], base, 'iig-' + impl.stem)
            if result.returncode == 0 and relative.parts[0] == 'Tests':
                impl.write_text('#if DEBUG || DEVELOPMENT\n' + impl.read_text() + '\n#endif\n')
            record('iokit', token, impl, definition)
            if result.returncode:rows[-1]['passed'] = False
    report = {'generated_sources': rows, 'commands': commands, 'iig_available': bool(iig),
              'syscalls_master_sha256': sha(master_source), 'makesyscalls_sha256': sha(makesyscalls),
              'seed_defines': [], 'synthetic_board_inputs': True, 'whole_kernel_build': False}
    (private / 'native-extra-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'extra_sources_generated': sum(r['passed'] for r in rows),
                      'attempted': len(rows), 'iig_available': bool(iig)}), flush=True)


if __name__ == '__main__':main()
