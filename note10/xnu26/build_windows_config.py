"""Build the actual public XNU config host tool in an isolated Windows stage."""
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys
from prepare_build_selection import ROOT

TOOLROOT = ROOT / 'host-tools/windows-build'
LLVM = TOOLROOT / 'llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin'
FLEX = TOOLROOT / 'winflexbison-2.5.25'


def main():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    reference = json.loads((ROOT / target['research_directory'] / 'xnu-reference.json').read_text())
    source = ROOT / reference['source_directory'] / 'SETUP/config'
    private = ROOT / 'note10/private/windows-config'
    stage = private / 'source'
    stage.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for path in source.iterdir():
        if path.suffix not in ('.c', '.h', '.l', '.y'):
            continue
        raw = path.read_bytes()
        hashes[path.name] = hashlib.sha256(raw).hexdigest()
        (stage / path.name).write_bytes(raw)
    native_mac = sys.platform == 'darwin'
    compiler = subprocess.check_output(['xcrun', '-f', 'clang']).decode().strip() if native_mac else str(LLVM / 'x86_64-w64-mingw32-clang.exe')
    bison = shutil.which('bison') if native_mac else str(FLEX / 'win_bison.exe')
    flex = shutil.which('flex') if native_mac else str(FLEX / 'win_flex.exe')
    compat = ['-include', 'strings.h'] if native_mac else ['-include', str(ROOT / 'note10/xnu26/windows_config_compat.h')]
    host_sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path']).decode().strip() if native_mac else None
    host_flags = ['-isysroot', host_sdk] if native_mac else []
    commands = [
        [bison, '-y', '-d', '-o', 'parser.c', 'parser.y'],
        [flex, *([] if native_mac else ['--wincompat']), '--header-file=lexer.yy.h', '-o', 'lexer.yy.c', 'lexer.l'],
        [compiler, '-std=gnu11', '-O2', '-DYY_NO_INPUT', *host_flags, *compat,
         '-I.', 'externs.c', 'main.c', 'mkheaders.c', 'mkioconf.c', 'mkmakefile.c',
         'openp.c', 'searchp.c', 'lexer.yy.c', 'parser.c', '-o', str(private / 'config.exe')],
    ]
    for i, command in enumerate(commands):
        result = subprocess.run(command, cwd=stage, capture_output=True, timeout=60)
        (private / ('build-' + str(i) + '.log')).write_bytes(result.stdout + result.stderr)
        if result.returncode:
            print(result.stderr.decode('utf-8', errors='replace'))
            raise SystemExit(result.returncode)
    report = {'source_commit': reference['commit'], 'source_sha256': hashes, 'commands': commands,
              'host_compat_sha256': hashlib.sha256((ROOT / 'note10/xnu26/windows_config_compat.h').read_bytes()).hexdigest(),
              'host_exe_sha256': hashlib.sha256((private / 'config.exe').read_bytes()).hexdigest(),
              'compiler_version': subprocess.check_output([compiler, '--version']).decode(),
              'host_platform': sys.platform, 'host_sdk': host_sdk, 'kernel_built': False, 'device_operations': []}
    (private / 'build-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'host_config_built': True, 'platform': sys.platform, 'kernel_built': False}))


if __name__ == '__main__':
    main()
