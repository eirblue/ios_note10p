"""Generate Mach export and kernel interfaces from the selected source on macOS.

Uses upstream MIG header lists and kernel user/server modes. Does not claim to
generate BSD/IOKit interfaces or to compile/link the generated server sources.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from prepare_build_selection import ROOT


def header_list(text, variable):
    match = re.search(r'^' + variable + r'\s*=\s*(.*)$', text.replace('\\\n', ' '), re.M)
    if not match:raise ValueError('Missing upstream MIG list: ' + variable)
    names = match.group(1).split()
    if any(not re.fullmatch(r'[a-zA-Z0-9_]+\.h', n) for n in names):
        raise ValueError('Unsupported MIG header list')
    return names


def main():
    if sys.platform != 'darwin':raise SystemExit('Native MIG generation requires macOS')
    private = ROOT / 'note10/private/windows-xnu'
    configured = json.loads((private / 'configure-result.json').read_text())
    source = ROOT / configured['source_directory']
    config = private / 'configured/DEVELOPMENT/osfmk'
    text = (config / 'Makefile').read_text()
    flags = shlex.split(re.search(r'^export CONFIG_DEFINES =(.*)$', text, re.M).group(1))
    mig = subprocess.check_output(['xcrun', '-f', 'mig']).decode().strip()
    base = private / 'native-mig'
    makefile = source / 'osfmk/mach/Makefile'
    rules = makefile.read_text()
    includes = [config, source / 'EXTERNAL_HEADERS']
    includes += [private / 'source-exports' / c for c in ('osfmk','bsd','pexpert','libkern','iokit','libsa','security','san')]
    includes += [source / c for c in ('osfmk','bsd','pexpert','libkern','iokit','libsa','security','san')]
    common = [mig, '-arch', 'arm64', '-isysroot', os.environ['N10_SDKROOT'], '-novouchers',
              '-Darm64', '-DARM64', '-D__ARM64__', '-DKERNEL', '-DKERNEL_PRIVATE', '-DXNU_KERNEL_PRIVATE',
              '-DXNU_TARGET_OS_IOS', '-DARM64_BOARD_CONFIG_EXYNOS9825',
              '-DN10_BOARD_SCHEMA=1', '-DN10_ICACHE_LINE_LOG2=6', '-DN10_DCACHE_LINE_LOG2=6',
              '-DN10_MAX_CACHE_LINE_LOG2=7', '-DN10_KERNEL_PAGE_SHIFT=14', *flags]
    # The mig shell driver forwards joined -I/-D options; separate -I arguments
    # and clang's -include operand are parsed as input filenames by that driver.
    # Upstream MIGFLAGS uses joined include flags and CONFIG_DEFINES as well.
    for directory in includes:common.append('-I' + str(directory))
    rows = []
    modes = [('export', 'MIG_UUHDRS', False, []), ('export', 'MIG_USHDRS', True, []),
             ('kernel', 'MIG_KUHDRS', False, ['-DMACH_KERNEL_PRIVATE', '-DKERNEL_USER=1', '-DEXC_SERVER_AUDITTOKEN=1', '-DMACH_EXC_SERVER_AUDITTOKEN=1', '-maxonstack', '1024']),
             ('kernel', 'MIG_KSHDRS', True, ['-DMACH_KERNEL_PRIVATE', '-DKERNEL_SERVER=1', '-mach_msg2'])]
    for mode, variable, server, extra in modes:
        directory = base / mode / 'osfmk/mach'; directory.mkdir(parents=True, exist_ok=True)
        for name in header_list(rules, variable):
            stem = name.removesuffix('_server.h') if server else name.removesuffix('.h')
            definition = source / 'osfmk/mach' / (stem + '.defs')
            out = directory / name
            command = [*common, *extra, '-user', '/dev/null', '-server', '/dev/null',
                       '-header', '/dev/null' if server else str(out),
                       '-sheader', str(out) if server else '/dev/null', str(definition)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            log = base / (mode + '-' + name + '.log')
            log.write_text(result.stdout + result.stderr)
            passed = result.returncode == 0 and out.is_file()
            rows.append({'mode': mode, 'header': name, 'passed': passed, 'command': command,
                         'definition_sha256': hashlib.sha256(definition.read_bytes()).hexdigest(),
                         'header_sha256': hashlib.sha256(out.read_bytes()).hexdigest() if passed else None})
    report = {'interfaces': rows, 'all_passed': all(r['passed'] for r in rows),
              'source_makefile_sha256': hashlib.sha256(makefile.read_bytes()).hexdigest(),
              'scope': 'Mach export/kernel headers only; BSD/IOKit generated interfaces still borrowed',
              'generated_c_compiled': False, 'synthetic_board_inputs': True, 'whole_kernel_build': False}
    (private / 'native-mig-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'native_mig_headers': sum(r['passed'] for r in rows), 'attempted': len(rows),
                      'all_passed': report['all_passed']}), flush=True)


if __name__ == '__main__':main()
