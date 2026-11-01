"""Build the new opt-in KAT object only; no old models, Image, provider execution or device."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from build_xnu_runtime_plan_component import acquire, extract, parse_dependencies, COMMIT, DEFCONFIG
from pre_pm_archive_contract import archive_identity, stable_archive
from prepare_sha256_runtime_kat import install, TARGET, OPTION

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = (
    'note10/device_test/sha256_runtime_kat.c',
    'note10/device_test/prepare_sha256_runtime_kat.py',
    'note10/device_test/decode_sha256_runtime_kat.py',
    'note10/device_test/build_sha256_runtime_kat.py',
    'note10/device_test/test_sha256_runtime_kat.py',
    'note10/device_test/sha256_runtime_kat_fixture.c',
    '.github/workflows/note10-sha256-runtime-kat.yml',
)
INPUT_HELPERS = (
    'note10/device_test/build_xnu_runtime_plan_component.py',
    'note10/device_test/prepare_xnu_runtime_plan.py',
    'note10/device_test/pre_pm_archive_contract.py',
    'note10/device_test/decode_reservation.py',
)
SETTINGS = {'CRYPTO': 'y', 'CRYPTO_HASH': 'y', 'CRYPTO_SHA256': 'y', OPTION: 'y',
            'MODVERSIONS': 'y', 'LTO': 'n', 'LTO_CLANG': 'n',
            'FTRACE_MCOUNT_RECORD': 'n', 'STACK_VALIDATION': 'n',
            'LOCALVERSION_AUTO': 'n', 'INITRAMFS_SOURCE': '""',
            'LOCALVERSION': '"-v70-sha256-kat-object"'}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n', encoding='utf8')


def capture(source, objects, compiler_include, out):
    """Retain actual compiler prerequisites as inputs, without semantic replay."""
    cmd = objects/'drivers/misc/.note10_sha256_kat.o.cmd'
    ordinary, wildcard = parse_dependencies(cmd.read_text())
    required = ['drivers/misc/note10_sha256_kat.c', '.config',
                'include/generated/autoconf.h', 'include/config/auto.conf']
    records, absent = {}, []
    roots = [('objects', objects.resolve()), ('source', source.resolve()),
             ('compiler-include', compiler_include.resolve())]

    def retain(name, optional=False):
        original = Path(name)
        candidates = [original] if original.is_absolute() else [objects/original, source/original]
        for path in candidates:
            resolved = path.resolve()
            bound = [(label, root) for label, root in roots if resolved.is_relative_to(root)]
            if path.is_file() and not path.is_symlink() and bound:
                label, root = bound[0]
                key = label+'/'+resolved.relative_to(root).as_posix()
                target = out/'prerequisites'/key
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(resolved, target)
                records[key] = sha(target)
                return
        if optional:
            absent.append(name)
        else:
            raise ValueError('missing/outside actual KAT prerequisite: '+name)

    for name in [*ordinary, *required]:
        retain(name)
    for group in wildcard:
        for name in group:
            retain(name, True)
    shutil.copyfile(cmd, out/'actual-object.cmd')
    shutil.copyfile(objects/TARGET, out/'note10_sha256_kat.o')
    save(out/'dependencies.json', {'files_sha256': records, 'optional_absent': sorted(absent)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args()
    out = args.output.resolve()
    private = (ROOT/'note10/private').resolve()
    workspace = out.with_name(out.name+'-workspace')
    if (sys.platform != 'linux' or not out.is_relative_to(private) or out == private or
            out.exists() or workspace.exists() or not 1 <= args.jobs <= 16):
        raise ValueError('fresh private Linux output/workspace and bounded jobs required')
    archive = args.archive.resolve() if args.archive else out.with_name(out.name+'-kernel-input.tar.gz')
    if archive.is_relative_to(out) or archive.is_relative_to(workspace):
        raise ValueError('immutable archive must stay outside generated evidence/workspace')
    out.mkdir(parents=True)
    commands = []
    env = dict(os.environ, PLATFORM_VERSION='11', ANDROID_MAJOR_VERSION='r')

    def run(argv, log):
        row = {'argv': [str(x) for x in argv], 'log': log, 'completed': False}
        commands.append(row)
        save(out/'commands.json', commands)
        target = out/log
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('wb') as stream:
            result = subprocess.run(row['argv'], stdout=stream, stderr=subprocess.STDOUT,
                                    env=env, timeout=1800)
        row.update(completed=True, returncode=result.returncode)
        save(out/'commands.json', commands)
        if result.returncode:
            raise ValueError('KAT object build failed: '+log)

    try:
        manifest = {name: sha(ROOT/name) for name in (*PUBLIC, *INPUT_HELPERS)}
        ci = {name: os.environ.get(name) for name in
              ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB')}
        identity = hashlib.sha256(json.dumps({'source': manifest, 'ci': ci}, sort_keys=True).encode()).hexdigest()[:32]
        for name in manifest:
            target = out/'source'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, target)
        save(out/'source-manifest.json', manifest)
        if not args.archive:
            acquire(archive)
        before = archive_identity(archive)
        save(out/'archive-input.json', before)
        workspace.mkdir()
        source = extract(archive, workspace/'source')
        objects = workspace/'objects'
        objects.mkdir()
        overlay = install(source, identity)
        save(out/'overlay.json', {'identity': identity, 'files_sha256': overlay, 'default_enabled': False})
        for name in overlay:
            target = out/'overlay'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source/name, target)
        run(['clang-14', '-print-file-name=include'], 'tools/compiler-include.log')
        include = Path((out/'tools/compiler-include.log').read_text().strip())
        tools = {}
        for tool in ('clang-14', 'gcc', 'make', 'aarch64-linux-gnu-gcc',
                     'arm-linux-gnueabi-gcc', 'aarch64-linux-gnu-ld'):
            path = shutil.which(tool)
            if not path:
                raise ValueError('required Kbuild tool missing: '+tool)
            tools[tool] = {'path': str(Path(path).resolve()), 'sha256': sha(path)}
        save(out/'toolchain.json', tools)
        make = ['make', '-C', source, 'O='+str(objects), 'ARCH=arm64', 'CC=clang-14',
                'CROSS_COMPILE=aarch64-linux-gnu-', 'CLANG_TRIPLE=aarch64-linux-gnu-',
                'CROSS_COMPILE_ARM32=arm-linux-gnueabi-',
                'GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/', 'HOSTCC=gcc',
                'HOSTCFLAGS=-Wno-error=deprecated-declarations']
        run([*make, DEFCONFIG], 'build/01-defconfig.log')
        for index, (name, value) in enumerate(SETTINGS.items()):
            action = ['--enable', name] if value == 'y' else ['--disable', name] if value == 'n' else ['--set-str', name, value[1:-1]]
            run([source/'scripts/config', '--file', objects/'.config', *action], f'build/settings/{index:02}.log')
        run([*make, 'olddefconfig'], 'build/02-olddefconfig.log')
        config = (objects/'.config').read_text()
        for name, value in SETTINGS.items():
            line = '# CONFIG_'+name+' is not set' if value == 'n' else 'CONFIG_'+name+'='+value
            if line not in config.splitlines() and not (value == 'n' and 'CONFIG_'+name+'=' not in config):
                raise ValueError('fresh effective KAT config differs: '+name)
        # Exactly one new kernel TU; no historical object or native fixture target.
        run([*make, 'V=1', '-j'+str(args.jobs), TARGET], 'build/03-new-object.log')
        capture(source, objects, include, out)
        stable_archive(archive, before)
        result = dict(schema=1, version='v70', passed=True, kernel_commit=COMMIT,
                      build_evidence_id=identity, source_sha256=manifest, ci_context=ci,
                      settings=SETTINGS, target=TARGET, executed_fixture_commands=0,
                      kernel_object_executed=False, provider_executed=False,
                      Image_or_BOOT_built=False, deployment_ready=False,
                      device_operations=[], runtime_availability_proven=False,
                      recovery_integration_proven=False, archive_input=before)
        result['files_sha256'] = {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()}
        save(out/'result.json', result)
    except Exception as error:
        save(out/'failure.json', {'accepted': False, 'error': repr(error), 'device_operations': []})
        raise


if __name__ == '__main__':
    main()
