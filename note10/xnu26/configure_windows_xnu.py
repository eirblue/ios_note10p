"""Run the native upstream config tool on an isolated fully patched source copy."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from prepare_build_selection import ROOT

COMPONENTS = ('osfmk', 'bsd', 'iokit', 'libkern', 'pexpert', 'libsa', 'security', 'san')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    reference = json.loads((ROOT / target['research_directory'] / 'xnu-reference.json').read_text())
    original = ROOT / reference['source_directory']
    private = ROOT / 'note10/private/windows-xnu'
    source = private / ('xnu-' + reference['commit'])
    source.parent.mkdir(exist_ok=True)
    print('Copying public source into isolated build stage', flush=True)
    shutil.copytree(original, source, dirs_exist_ok=True)
    patches = ROOT / 'note10/xnu26/patches'
    series = [s for s in (patches / 'series').read_text().splitlines() if s and not s.startswith('#')]
    changed = set()
    for name in series:
        lines = (patches / name).read_text(encoding='utf-8').splitlines()
        for i, line in enumerate(lines):
            if not line.startswith('+++ b/'):
                continue
            relative = Path(line[6:])
            path = source / relative
            if not path.resolve().is_relative_to(source.resolve()) or '.git' in relative.parts:
                raise ValueError('Unsafe patch input')
            changed.add(relative)
            if i and lines[i-1] == '--- /dev/null' and path.exists():
                path.unlink()  # Only prior generated additions under this isolated source stage.
    original_hashes = {n.as_posix(): digest(original / n) if (original / n).is_file() else None for n in changed}
    for name in series:
        subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '--directory', source.relative_to(ROOT).as_posix(),
                        (patches / name).relative_to(ROOT).as_posix()], cwd=ROOT, check=True)
    config_exe = ROOT / 'note10/private/windows-config/config.exe'
    host_build = json.loads((config_exe.parent / 'build-result.json').read_text())
    if digest(config_exe) != host_build['host_exe_sha256']:
        raise ValueError('Windows config tool hash changed')
    master = ROOT / 'note10/private/xnu26-master'
    master_test = json.loads((master / 'test-result.json').read_text())
    configured = []
    env = dict(os.environ); env['VPATH'] = ''
    for variant in ('RELEASE', 'DEVELOPMENT', 'DEBUG'):
        config_text = master / ('config.' + variant + '_ARM64')
        expected = next(c['text_sha256'] for c in master_test['config_texts'] if c['variant'] == variant)
        if digest(config_text) != expected:
            raise ValueError('SoC configuration text hash changed')
        for component in COMPONENTS:
            output = private / 'configured' / variant / component
            output.mkdir(parents=True, exist_ok=True)
            # The upstream tool appends meta_features includes only when creating
            # a feature header for the first time. Reuse must preserve both.
            config_file = output / 'config.input'
            text = config_text.read_text() + '\nbuilddir "."\nobjectdir "' + output.as_posix() + \
                   '"\nsourcedir "' + source.as_posix() + '"\n'
            config_file.write_text(text, encoding='utf-8', newline='\n')
            command = [str(config_exe), '-c', str(source / component / 'conf'), str(config_file)]
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=30)
            (output / 'config.log').write_bytes(result.stdout + result.stderr)
            if result.returncode:
                print(result.stdout.decode('utf-8', errors='replace'))
                print(result.stderr.decode('utf-8', errors='replace'))
                raise SystemExit(result.returncode)
            headers = {p.name: digest(p) for p in output.glob('*.h')}
            if not (output / 'Makefile').exists() or not headers:
                raise ValueError('Native config did not generate Makefile/headers: ' + component)
            configured.append({'variant': variant, 'component': component, 'headers': headers,
                               'makefile_sha256': digest(output / 'Makefile'),
                               'input_sha256': digest(config_file)})
            print(variant + '/' + component + ': ' + str(len(headers)) + ' headers', flush=True)
    for n, expected in original_hashes.items():
        current = digest(original / n) if (original / n).is_file() else None
        if current != expected:
            raise ValueError('Original source changed')
    report = {'source_commit': reference['commit'], 'source_directory': source.relative_to(ROOT).as_posix(),
              'patched_source_sha256': {n.as_posix(): digest(source / n) for n in changed},
              'patch_sha256': {n: digest(patches / n) for n in series}, 'host_exe_sha256': digest(config_exe),
              'configured': configured, 'native_config_executed': True, 'public_source_unchanged': True,
              'whole_kernel_build': False, 'device_operations': []}
    (private / 'configure-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'components': len(COMPONENTS), 'configurations': len(configured),
                      'native_config_executed': True, 'whole_kernel_build': False}))


if __name__ == '__main__':
    main()
