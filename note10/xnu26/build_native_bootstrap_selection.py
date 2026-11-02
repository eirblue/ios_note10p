"""One PC-only build of the 15 actually configured Exynos bootstrap sources.

Run only in a fresh macOS CI checkout. No kernel link, candidate archive or device.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

from prepare_native_bootstrap_selection import COMMIT, OPTION, PATCH_NAME, PINS, ROOT, SOURCES, patch_bytes

COMPONENTS = ('osfmk', 'bsd', 'iokit', 'libkern', 'pexpert', 'libsa', 'security', 'san')
PRIVATE = ROOT / 'note10/private'
JOB = 'native-bootstrap-selection'
WORKFLOW = '.github/workflows/note10-native-bootstrap-selection.yml'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def private(path):
    path = Path(path).absolute()
    if path.resolve() != path or not path.is_relative_to(PRIVATE) or path == PRIVATE:
        raise ValueError('ordinary private child path required')
    return path


def ci_context():
    keys = ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB',
            'GITHUB_WORKFLOW_REF', 'GITHUB_WORKFLOW_SHA', 'GITHUB_REPOSITORY')
    result = {k: os.environ.get(k, '') for k in keys}
    if (not re.fullmatch('[0-9a-f]{40}', result['GITHUB_SHA']) or
        result['GITHUB_WORKFLOW_SHA'] != result['GITHUB_SHA'] or
        not all(re.fullmatch('[1-9][0-9]*', result[k]) for k in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT')) or
        result['GITHUB_JOB'] != JOB or result['GITHUB_REPOSITORY'] != 'eirblue/ios_note10p' or
        not result['GITHUB_WORKFLOW_REF'].startswith('eirblue/ios_note10p/' + WORKFLOW + '@')):
        raise ValueError('closed producing workflow/head/run/attempt/job context required')
    return result


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def run(command, cwd, log, *, data=None, env=None):
    result = subprocess.run([str(x) for x in command], cwd=cwd, input=data,
                            capture_output=True, timeout=240, env=env)
    Path(log).parent.mkdir(parents=True, exist_ok=True)
    Path(log).write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('necessary build command failed: ' + Path(log).name)
    return result.stdout


def definitions(makefile):
    matches = re.findall(r'^export CONFIG_DEFINES =(.*)$', makefile, re.M)
    if len(matches) != 1:
        raise ValueError('one real config definition assignment required')
    return shlex.split(matches[0])


def memberships(makefiles):
    """Count before deduplication, including duplicates within one owner."""
    owners = {name: [] for name in SOURCES}
    for component, text in makefiles.items():
        if component not in COMPONENTS:
            raise ValueError('unknown source owner')
        text = text.replace('\\\n', ' ')
        for key in ('CFILES', 'SFILES'):
            matches = re.findall(r'^' + key + r'=(.*)$', text, re.M)
            if len(matches) != 1:
                raise ValueError('one real source assignment required: ' + key)
            for token in matches[0].split():
                prefix = '$(SOURCE_DIR)/'
                if token.startswith(prefix) and token[len(prefix):] in owners:
                    name = token[len(prefix):]
                    owners[name].append((component, key))
    return owners


def selected_sources(makefiles):
    owners = memberships(makefiles)
    for name, found in owners.items():
        expected = ('osfmk', 'CFILES' if name.endswith('.c') else 'SFILES')
        if found != [expected]:
            raise ValueError('source must have exactly one native owner: ' + name)
    return tuple(SOURCES)


def selected_text(source, variant, log):
    """Use the retained source's actual doconf selector, not a config emulator."""
    text = (source / 'SETUP/config/doconf').read_text()
    start = text.index('    sed -n \\\n')
    end = text.index("' >$SYSCONF.new", start) + 1
    master = (source / 'config/MASTER').read_bytes()
    soc = (source / 'config/MASTER.arm64.exynos9825').read_bytes()
    if re.search(rb'^#(?:if|elif|else|endif)\b', master + soc, re.M):
        raise ValueError('unresolved MASTER input')
    data = master + soc + ('\n+' + variant + '\n').encode() + master + soc
    return run(['/bin/sh', '-c', 'export PATH=/usr/bin:/bin\n' + text[start:end]],
               source, log, data=data).decode()


def configure(source, tool, output, variant='DEVELOPMENT', component='osfmk', *, extras=(),
              option=True, conf_directory=None):
    output.mkdir(parents=True, exist_ok=False)
    text = selected_text(source, variant, output / 'selector.log')
    if not option:
        text = re.sub(r'^options\s+' + OPTION + r'\s*$', '', text, flags=re.M)
    text += '\n' + ''.join('options ' + x + '\n' for x in extras)
    text += ('\nbuilddir "."\nobjectdir "' + output.as_posix() +
             '"\nsourcedir "' + source.as_posix() + '"\n')
    config = output / 'config.input'
    config.write_text(text, encoding='utf-8')
    env = dict(os.environ, VPATH='')
    run([tool, '-c', conf_directory or source / component / 'conf', config],
        ROOT, output / 'config.log', env=env)
    return (output / 'Makefile').read_text()


def build_config_tool(source, work, output):
    stage = work / 'config-tool'
    stage.mkdir()
    for p in (source / 'SETUP/config').iterdir():
        if p.suffix in ('.c', '.h', '.l', '.y'):
            shutil.copyfile(p, stage / p.name)
    compiler = subprocess.check_output(['xcrun', '-f', 'clang']).decode().strip()
    sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path']).decode().strip()
    tool = stage / 'config'
    commands = [
        ['bison', '-y', '-d', '-o', 'parser.c', 'parser.y'],
        ['flex', '--header-file=lexer.yy.h', '-o', 'lexer.yy.c', 'lexer.l'],
        [compiler, '-std=gnu11', '-O2', '-DYY_NO_INPUT', '-isysroot', sdk,
         '-include', 'strings.h', '-I.', 'externs.c', 'main.c', 'mkheaders.c',
         'mkioconf.c', 'mkmakefile.c', 'openp.c', 'searchp.c', 'lexer.yy.c',
         'parser.c', '-o', str(tool)],
    ]
    for n, command in enumerate(commands):
        run(command, stage, output / ('host-config-' + str(n) + '.log'))
    return tool, compiler, sdk


def provision(work, output, *, ci=None, leaf=False, checked=False):
    if sys.platform != 'darwin' or os.environ.get('GITHUB_ACTIONS') != 'true':
        raise ValueError('fresh macOS CI only')
    ci = ci_context() if ci is None else ci
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip() != ci['GITHUB_SHA']:
        raise ValueError('checkout/head mismatch')
    work.mkdir(parents=True, exist_ok=False)
    output.mkdir(parents=True, exist_ok=False)
    state = {'phase': 'provisioning', 'ci_context': ci, 'passed': False,
             'device_operations': [], 'kernel_linked': False, 'synthetic_board_inputs': True}
    write_json(output / 'result.json', state)
    source = work / 'source'
    source.mkdir()
    run(['git', 'init', '-q'], source, output / 'source-init.log')
    run(['git', 'fetch', '--depth=1', 'https://github.com/apple-oss-distributions/xnu.git', COMMIT],
        source, output / 'source-fetch.log')
    run(['git', 'checkout', '-q', '--detach', 'FETCH_HEAD'], source, output / 'source-checkout.log')
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source).decode().strip() != COMMIT:
        raise ValueError('exact public source checkout required')
    patches = ROOT / 'note10/xnu26/patches'
    names = (patches / 'series').read_text().splitlines()
    clock_patch = '0011-exynos9825-early-counter-clock.patch'
    leaf_patch='0012-exynos9825-bounded-leaf-bootstrap.patch'
    checked_patch='0013-exynos9825-checked-dynamic-ptpage.patch'
    if checked and not leaf:raise ValueError('checked allocator requires the selected mapper')
    if (len(names) not in (10,11,12,13) or names[9] != PATCH_NAME or
        (len(names)>=11 and names[10]!=clock_patch) or
        (len(names)>=12 and names[11]!=leaf_patch) or
        (len(names)==13 and names[12]!=checked_patch) or
        (leaf and len(names)<12) or (checked and len(names)!=13)):
        raise ValueError('closed native bootstrap/clock/optional leaf series required')
    names=names if checked else (names[:12] if leaf else names[:11])
    for n, name in enumerate(names[:9]):
        run(['git', '-c', 'core.autocrlf=false', 'apply', patches / name],
            source, output / ('patch-' + str(n + 1) + '.log'))
    before = {n: (source / n).read_bytes() for n in PINS}
    if patch_bytes(before) != (patches / PATCH_NAME).read_bytes():
        raise ValueError('published patch differs from pinned transform')
    (work / 'baseline-files.arm64').write_bytes(before['osfmk/conf/files.arm64'])
    run(['git', '-c', 'core.autocrlf=false', 'apply', patches / PATCH_NAME],
        source, output / 'patch-10.log')
    if len(names) >= 11:
        from prepare_exynos_early_clock import REL as CLOCK_REL, patch_bytes as clock_patch_bytes
        component = (ROOT / 'note10/xnu26/exynos_early_clock.c').read_bytes()
        if clock_patch_bytes((source / CLOCK_REL).read_bytes(), component) != (patches / clock_patch).read_bytes():
            raise ValueError('early-clock kernel patch differs from the tested production component')
        run(['git', '-c', 'core.autocrlf=false', 'apply', patches / clock_patch],
            source, output / 'patch-11.log')
    if leaf:
        from prepare_exynos_leaf_mapper import PINS as LEAF_PINS, patch_bytes as leaf_patch_bytes
        if leaf_patch_bytes({n:(source/n).read_bytes() for n in LEAF_PINS}) != (patches/leaf_patch).read_bytes():
            raise ValueError('leaf production include differs from the tested component')
        run(['git','-c','core.autocrlf=false','apply',patches/leaf_patch],source,output/'patch-12.log')
    if checked:
        from prepare_exynos_checked_ptpage import REL as CHECKED_REL, patch_bytes as checked_patch_bytes
        if checked_patch_bytes((source/CHECKED_REL).read_bytes()) != (patches/checked_patch).read_bytes():
            raise ValueError('checked allocator kernel include differs from tested production component')
        run(['git','-c','core.autocrlf=false','apply',patches/checked_patch],source,output/'patch-13.log')
    tool, compiler, sdk = build_config_tool(source, work, output)
    context = dict(ci_context=ci, source=str(source), tool=str(tool), compiler=compiler,
                   sdk=sdk, public_source_commit=COMMIT, output=str(output), phase='provisioned',
                   patch_sha256={n: sha(patches / n) for n in names})
    write_json(work / 'context.json', context)
    state.update(phase='provisioned', public_source_commit=COMMIT, patch_sha256=context['patch_sha256'])
    write_json(output / 'result.json', state)


def load_context(work):
    context = json.loads((work / 'context.json').read_text())
    if context['ci_context'] != ci_context() or context['public_source_commit'] != COMMIT:
        raise ValueError('current producing source/job context required')
    if Path(context['source']) != work / 'source' or Path(context['tool']) != work / 'config-tool/config':
        raise ValueError('closed fresh workspace paths required')
    return context


def common_flags(source, configured, sdk):
    flags = ['--target=arm64-apple-ios26.5.2', '-march=armv8.2-a+crypto', '-mcpu=generic',
             '-O2', '-ffreestanding', '-fno-builtin', '-fno-common', '-fblocks', '-nostdlibinc',
             '-fno-stack-protector', '-mno-implicit-float', '-mstrict-align', '-ferror-limit=8',
             '-Darm64', '-DARM64', '-D__ARM64__', '-DLP64', '-DAPPLE', '-DKERNEL',
             '-DKERNEL_PRIVATE', '-DXNU_KERNEL_PRIVATE', '-DPRIVATE', '-D__API__=v4',
             '-DPAGE_SIZE_FIXED', '-DARM_LARGE_MEMORY=0', '-DVM_KERNEL_LINK_ADDRESS=0xfffffff007004000',
             '-DCURRENT_MACHINE_CONFIG_LC=exynos9825', '-DXNU_TARGET_OS_IOS', '-DXNU_PLATFORM_iPhoneOS',
             '-DARM64_BOARD_CONFIG_EXYNOS9825', '-DN10_BOARD_SCHEMA=1',
             '-DN10_ICACHE_LINE_LOG2=6', '-DN10_DCACHE_LINE_LOG2=6',
             '-DN10_MAX_CACHE_LINE_LOG2=7', '-DN10_KERNEL_PAGE_SHIFT=14',
             '-include', str(configured / 'meta_features.h'), '-isysroot', sdk,
             '-DIMAGE4_STRIP_AVAILABILITY=1']
    flags += definitions((configured / 'Makefile').read_text())
    private_root = PRIVATE / 'windows-xnu'
    includes = [private_root / 'native-link/include', configured, source / 'EXTERNAL_HEADERS',
                private_root / 'native-mig/kernel/osfmk', private_root / 'native-mig/export/osfmk',
                private_root / 'generated-extra/bsd']
    includes += [private_root / 'source-exports' / c for c in (*COMPONENTS, 'EXTERNAL_HEADERS')]
    includes += [private_root / 'configured/DEVELOPMENT' / c for c in COMPONENTS if c != 'osfmk']
    includes += [source / c for c in (*COMPONENTS, '.')]
    includes += [source / 'osfmk/libsa', source / 'EXTERNAL_HEADERS/corecrypto',
                 ROOT / 'host-tools/kdk/headers/KDK.pkg/System/Library/KernelSupport',
                 ROOT / 'host-tools/kdk/headers/KDK_SDK.pkg/System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders/platform']
    includes += [Path(sdk) / p for p in ('System/Library/Frameworks/Kernel.framework/Versions/A/Headers',
                 'System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders',
                 'System/Library/Frameworks/Kernel.framework/Headers',
                 'System/Library/Frameworks/Kernel.framework/PrivateHeaders', 'usr/local/include', 'usr/include')]
    for p in includes:
        flags += ['-I', str(p)]
    return flags


def generated_headers(source, context, configured, output):
    """Only declaration/offset generation, never selected kernel C/C++ audits."""
    import cloud_compile
    import export_source_headers
    import generate_link_metadata
    from generate_native_mig import header_list
    private_root = PRIVATE / 'windows-xnu'
    env = dict(os.environ, N10_SDKROOT=context['sdk'], N10_MAKE=shutil.which('make') or 'make')
    with (output / 'declaration-generators.log').open('w') as log, contextlib.redirect_stdout(log):
        cloud_compile.sdk_declarations()
        export_source_headers.main()
        generate_link_metadata.main()
    bsd = private_root / 'generated-extra/bsd'
    bsd.mkdir(parents=True)
    master = bsd / 'syscalls.master'
    raw = subprocess.run(['xcrun', 'unifdef', str(source / 'bsd/kern/syscalls.master')],
                         capture_output=True, timeout=60)
    (output / 'syscalls-unifdef.log').write_bytes(raw.stderr)
    if raw.returncode not in (0, 1):
        raise ValueError('necessary syscall header input failed')
    master.write_bytes(raw.stdout)
    for mode in ('proto', 'header'):
        run(['/bin/sh', source / 'bsd/kern/makesyscalls.sh', master, mode], bsd,
            output / ('syscalls-' + mode + '.log'), env=env)
    (bsd / 'sys').mkdir()
    for name in ('sysproto.h', 'syscall.h'):
        shutil.copyfile(bsd / name, bsd / 'sys' / name)
    rules = (source / 'osfmk/mach/Makefile').read_text()
    mig = subprocess.check_output(['xcrun', '-f', 'mig']).decode().strip()
    base = private_root / 'native-mig'
    # Header lists are real upstream export/kernel dependencies. No generated C is compiled.
    for mode, variable, server, extra in [
        ('export', 'MIG_UUHDRS', False, []), ('export', 'MIG_USHDRS', True, []),
        ('kernel', 'MIG_KUHDRS', False, ['-DMACH_KERNEL_PRIVATE', '-DKERNEL_USER=1', '-DEXC_SERVER_AUDITTOKEN=1', '-DMACH_EXC_SERVER_AUDITTOKEN=1', '-maxonstack', '1024']),
        ('kernel', 'MIG_KSHDRS', True, ['-DMACH_KERNEL_PRIVATE', '-DKERNEL_SERVER=1', '-mach_msg2'])]:
        directory = base / mode / 'osfmk/mach'
        directory.mkdir(parents=True, exist_ok=True)
        for name in header_list(rules, variable):
            stem = name.removesuffix('_server.h') if server else name.removesuffix('.h')
            command = [mig, '-arch', 'arm64', '-target', 'arm64-apple-ios26.5.2',
                       '-march=armv8.2-a+crypto', '-mcpu=generic', '-isysroot', context['sdk'],
                       '-novouchers', '-Darm64', '-DARM64', '-D__ARM64__', '-DKERNEL',
                       '-DKERNEL_PRIVATE', '-DXNU_KERNEL_PRIVATE', '-DXNU_TARGET_OS_IOS',
                       '-DARM64_BOARD_CONFIG_EXYNOS9825', '-DN10_BOARD_SCHEMA=1',
                       '-DN10_ICACHE_LINE_LOG2=6', '-DN10_DCACHE_LINE_LOG2=6',
                       '-DN10_MAX_CACHE_LINE_LOG2=7', '-DN10_KERNEL_PAGE_SHIFT=14',
                       *definitions((configured / 'Makefile').read_text()), *extra]
            for p in [configured, source / 'EXTERNAL_HEADERS',
                      *[private_root / 'source-exports' / c for c in COMPONENTS],
                      *[source / c for c in COMPONENTS]]:
                command.append('-I' + str(p))
            command += ['-user', '/dev/null', '-server', '/dev/null',
                        '-header', '/dev/null' if server else str(directory / name),
                        '-sheader', str(directory / name) if server else '/dev/null',
                        str(source / 'osfmk/mach' / (stem + '.defs'))]
            run(command, ROOT, output / ('mig-' + mode + '-' + name + '.log'), env=env)


def build(work, output):
    context = load_context(work)
    if Path(context['output']) != output:
        raise ValueError('one producing output root required')
    state = json.loads((output / 'result.json').read_text())
    if state['phase'] != 'provisioned':
        raise ValueError('build is first-use only; no attempt replay')
    state['phase'] = 'building'
    write_json(output / 'result.json', state)
    source, tool = Path(context['source']), Path(context['tool'])
    private_root = PRIVATE / 'windows-xnu'
    if private_root.exists():
        raise ValueError('clean CI declaration/config output root required')
    private_root.mkdir()
    write_json(private_root / 'configure-result.json', {'source_directory': source.relative_to(ROOT).as_posix()})
    env = dict(os.environ)
    os.environ['N10_SDKROOT'] = context['sdk']
    os.environ['N10_MAKE'] = shutil.which('make') or 'make'
    try:
        makefiles = {}
        for component in COMPONENTS:
            directory = private_root / 'configured/DEVELOPMENT' / component
            cached = work / 'selection-DEVELOPMENT'
            if component == 'osfmk' and cached.is_dir():
                directory.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(cached, directory)
                # The tool's generated path fields must point at its final directory.
                for p in directory.iterdir():
                    if p.suffix in ('.h', '.s') or p.name in ('Makefile', 'config.input'):
                        p.write_text(p.read_text().replace(str(cached), str(directory)), encoding='utf-8')
                makefiles[component] = (directory / 'Makefile').read_text()
            else:
                makefiles[component] = configure(source, tool, directory, component=component)
        names = selected_sources(makefiles)
        configured = private_root / 'configured/DEVELOPMENT/osfmk'
        generated_headers(source, context, configured, output)
        flags = common_flags(source, configured, context['sdk'])
        cflags = ['-std=gnu11', '-mkernel', '-fno-c++-static-destructors',
                  '-ftrivial-auto-var-init=zero', '-fsigned-bitfields', '-fmerge-all-constants',
                  '-fno-strict-aliasing', '-momit-leaf-frame-pointer',
                  '-fno-branch-target-identification', '-mno-implicit-sme',
                  '-DMACH_KERNEL_PRIVATE', '-DMACH_KERNEL']
        # One intrinsic genassym compile; no old offset-comparison test.
        assembly = configured / 'genassym.S'
        command = [context['compiler'], *flags, *cflags, '-S', str(source / 'osfmk/arm64/genassym.c'),
                   '-fno-integrated-as', '-o', str(assembly)]
        genassym_command = list(command)
        run(command, ROOT, output / 'genassym.log')
        template = (source / 'osfmk/conf/Makefile.template').read_text()
        rule = next(l for l in template.splitlines() if 'sed -e' in l and 'DEFINITION__define__' in l)
        recipe = rule.split('$(_v)', 1)[1].split(' > $@')[0].replace('genassym.o', '"$1"').replace('$$', '$')
        assym = run(['/bin/sh', '-c', recipe, 'genassym', assembly], ROOT, output / 'assym-generation.log')
        if not assym:
            raise ValueError('empty generated assembly offsets')
        (configured / 'assym.s').write_bytes(assym)
        rows = []
        objects = output / 'objects'
        objects.mkdir()
        for name in names:
            obj = objects / (name.replace('/', '_') + '.o')
            language = cflags if name.endswith('.c') else ['-x', 'assembler-with-cpp', '-DASSEMBLER', '-D__ASSEMBLER__']
            command = [context['compiler'], *flags, *language, '-c', str(source / name), '-o', str(obj)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=120)
            obj.with_suffix('.log').write_bytes(result.stdout + result.stderr)
            rows.append(dict(source=name, owner='osfmk', command=command, passed=result.returncode == 0,
                             source_sha256=sha(source / name), object_sha256=sha(obj) if result.returncode == 0 else None))
            state.update(units=rows)
            write_json(output / 'result.json', state)
        state.update(phase='complete', passed=len(rows) == 15 and all(r['passed'] for r in rows),
                     selected_sources=list(names), candidate_archive_used=False, old_suites_executed=0,
                     configured_makefiles_sha256={c: sha(private_root / 'configured/DEVELOPMENT' / c / 'Makefile') for c in COMPONENTS},
                     genassym_command=genassym_command)
        write_json(output / 'result.json', state)
        if not state['passed']:
            raise RuntimeError('selected native source compilation failed')
    except BaseException as error:
        state.update(phase='failed', passed=False, error=type(error).__name__ + ': ' + str(error))
        write_json(output / 'result.json', state)
        raise
    finally:
        os.environ.clear()
        os.environ.update(env)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('provision', 'build'))
    p.add_argument('--work', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    work, output = private(args.work), private(args.output)
    if work == output or work.is_relative_to(output) or output.is_relative_to(work):
        p.error('disjoint private work and evidence roots required')
    try:
        (provision if args.action == 'provision' else build)(work, output)
    except Exception:
        # Detailed diagnostics stay in the sealed evidence, not public CI stdout.
        print('native bootstrap source build failed; private evidence retained', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
