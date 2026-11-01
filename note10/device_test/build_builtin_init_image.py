"""New forced minimal Linux PID1 Image; no old suites or device actions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
PUBLIC = (
    'note10/device_test/builtin_minimal_init.S',
    'note10/device_test/builtin_init_route.c',
    'note10/device_test/sha256_builtin_init.c',
    'note10/device_test/builtin_init_route.py',
    'note10/device_test/build_builtin_init_image.py',
    'note10/device_test/test_builtin_init_route.py',
    'note10/device_test/builtin_init_profile.py',
    'note10/device_test/sha256_kat_device_profile.py',
    'note10/device_test/auto_cycle.py',
    'note10/device_test/stage_phase2.py',
    'note10/device_test/build_boot_test_packages.py',
    'note10/device_test/materialize_auto_cycle.py',
    'note10/device_test/prepare_linux_boot.py',
    'note10/device_test/builtin_init_route_fixture.c',
    '.github/workflows/note10-builtin-init-route.yml',
)
INPUTS = (
    'note10/device_test/build_sha256_kat_recovery.py',
    'note10/device_test/prepare_sha256_kat_recovery.py',
    'note10/device_test/sha256_kat_recovery_work.c',
    'note10/device_test/sha256_kat_recovery.c',
    'note10/device_test/build_sha256_runtime_kat.py',
    'note10/device_test/build_xnu_runtime_plan_component.py',
    'note10/device_test/prepare_xnu_runtime_plan.py',
    'note10/device_test/pre_pm_archive_contract.py',
    'note10/device_test/prepare_sha256_runtime_kat.py',
    'note10/device_test/sha256_runtime_kat.c',
    'note10/device_test/auto_return.c',
    'note10/device_test/decode_sha256_runtime_kat.py',
    'note10/device_test/decode_reservation.py',
)
SETTINGS = {
    'NOTE10_SHA256_KAT_RECOVERY': 'y', 'NOTE10_BUILTIN_INIT_ROUTE': 'y',
    'CRYPTO': 'y', 'CRYPTO_HASH': 'y', 'CRYPTO_SHA256': 'y',
    'EXYNOS_REBOOT': 'y', 'SEC_REBOOT': 'y', 'BLK_DEV_INITRD': 'y',
    'INITRAMFS_SOURCE': '""', 'INITRAMFS_FORCE': 'y',
    'INITRAMFS_COMPRESSION_NONE': 'y',
    'INITRAMFS_COMPRESSION_GZIP': 'n', 'INITRAMFS_COMPRESSION_BZIP2': 'n',
    'INITRAMFS_COMPRESSION_LZMA': 'n', 'INITRAMFS_COMPRESSION_XZ': 'n',
    'INITRAMFS_COMPRESSION_LZO': 'n', 'INITRAMFS_COMPRESSION_LZ4': 'n',
    'CMDLINE': '""', 'CMDLINE_FORCE': 'n', 'CMDLINE_EXTEND': 'n', 'LOG_BUF_SHIFT': '21',
    'LTO': 'n', 'LTO_CLANG': 'n', 'FTRACE_MCOUNT_RECORD': 'n',
    'STACK_VALIDATION': 'n', 'LOCALVERSION_AUTO': 'n',
    'LOCALVERSION': '"-v72-builtin-init"',
}
# Reuse only accepted preparation and command-line helpers, never its main.


def retain_route_prerequisites(source, objects, out, compiler_include):
    """Actual new init/main and minimal-ELF compiler inputs, without a model."""
    from build_xnu_runtime_plan_component import parse_dependencies
    from build_sha256_runtime_kat import sha, save
    ordinary, wildcard = parse_dependencies((objects/'init/.main.o.cmd').read_text())
    dep = (out/'minimal-init.d').read_text().replace('\\\n', ' ')
    if ':' not in dep:
        raise ValueError('minimal ELF compiler dependency record missing')
    elf_inputs = dep.split(':', 1)[1].split()
    roots = [('objects', objects.resolve()), ('source', source.resolve()), ('repository', ROOT),
             ('clang-include', compiler_include.resolve()),
             ('aarch64-uapi', Path('/usr/aarch64-linux-gnu/include')),
             ('gcc-cross', Path('/usr/lib/gcc-cross/aarch64-linux-gnu'))]
    records, absent = {}, []
    def retain(name, optional=False):
        path = Path(name)
        for p in ([path] if path.is_absolute() else [objects/path, source/path]):
            resolved = p.resolve()
            bound = [(label, root) for label, root in roots if resolved.is_relative_to(root)]
            if p.is_file() and not p.is_symlink() and bound:
                label, root = bound[0]; key = label+'/'+resolved.relative_to(root).as_posix()
                target = out/'route-prerequisites'/key
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(resolved, target); records[key] = sha(target); return
        if optional: absent.append(name)
        else: raise ValueError('missing/outside actual route prerequisite: '+name)
    for name in (*ordinary, *elf_inputs): retain(name)
    for group in wildcard:
        for name in group: retain(name, True)
    save(out/'route-dependencies.json', {'files_sha256': records, 'optional_absent': sorted(absent)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    out = args.output.resolve()
    private = (ROOT/'note10/private').resolve()
    workspace = out.with_name(out.name+'-workspace')
    if (sys.platform != 'linux' or out == private or not out.is_relative_to(private) or
            out.exists() or workspace.exists() or not 1 <= args.jobs <= 8):
        raise ValueError('fresh bounded private Linux Image output/workspace required')
    archive = args.archive.resolve() if args.archive else out.with_name(out.name+'-kernel-input.tar.gz')
    if archive.is_relative_to(out) or archive.is_relative_to(workspace):
        raise ValueError('complete immutable archive must stay external')
    out.mkdir(parents=True)
    # Bind all local first-use input bytes before importing any local helper.
    manifest = {}
    for name in (*PUBLIC, *INPUTS):
        data = (ROOT/name).read_bytes()
        manifest[name] = hashlib.sha256(data).hexdigest()
        target = out/'source'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    from build_sha256_runtime_kat import sha, save, capture
    from build_xnu_runtime_plan_component import acquire, extract, COMMIT, DEFCONFIG
    from pre_pm_archive_contract import archive_identity, stable_archive
    from prepare_sha256_kat_recovery import TARGET, KERNEL_PINS
    from builtin_init_route import install, API_PINS, elf_manifest, cpio
    from build_sha256_kat_recovery import BUILD_INPUT_PINS, bootloader_cmdline_policy, prepare_image_inputs
    save(out/'source-manifest.json', manifest)
    ci = {name: os.environ.get(name) for name in
          ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB')}
    identity = hashlib.sha256(json.dumps({'source': manifest, 'ci': ci}, sort_keys=True).encode()).hexdigest()[:32]
    commands = []
    env = dict(os.environ, PLATFORM_VERSION='11', ANDROID_MAJOR_VERSION='r')

    def run(argv, log, timeout=1800):
        row = {'argv': [str(x) for x in argv], 'log': log, 'completed': False}
        commands.append(row)
        save(out/'commands.json', commands)
        path = out/log
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('wb') as stream:
            result = subprocess.run(row['argv'], stdout=stream, stderr=subprocess.STDOUT,
                                    env=env, timeout=timeout)
        row.update(completed=True, returncode=result.returncode)
        save(out/'commands.json', commands)
        if result.returncode:
            raise ValueError('new Image command failed: '+log)

    try:
        if not args.archive:
            acquire(archive)
        before = archive_identity(archive)
        save(out/'archive-input.json', before)
        workspace.mkdir()
        source = extract(archive, workspace/'source')
        objects = workspace/'objects'
        objects.mkdir()
        # Keep the unchanged reboot/init/crypto sources as current build inputs.
        for name in (*KERNEL_PINS, *BUILD_INPUT_PINS, *API_PINS, "usr/Kconfig", "include/linux/sched.h"):
            target = out/'stock-inputs'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source/name, target)
        overlay = install(source, identity)
        image_prep = prepare_image_inputs(source)
        save(out/'overlay.json', {'identity': identity, 'files_sha256': overlay,
                                  'image_preparation_sha256': image_prep,
                                  'default_enabled': False, 'cycle_slot_patched': False})
        for name in (*overlay, *image_prep):
            target = out/'overlay'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source/name, target)
        tools = {}
        for tool in ('clang-14', 'gcc', 'make', 'aarch64-linux-gnu-gcc',
                     'arm-linux-gnueabi-gcc', 'aarch64-linux-gnu-ld',
                     'aarch64-linux-gnu-nm', 'aarch64-linux-gnu-readelf'):
            path = shutil.which(tool)
            if not path:
                raise ValueError('Kbuild tool missing: '+tool)
            tools[tool] = {'path': str(Path(path).resolve()), 'sha256': sha(path)}
        save(out/'toolchain.json', tools)
        run(['clang-14', '-print-file-name=include'], 'tools/compiler-include.log')
        compiler_include = Path((out/'tools/compiler-include.log').read_text().strip())
        make = ['make', '-C', source, 'O='+str(objects), 'ARCH=arm64', 'CC=clang-14',
                'CROSS_COMPILE=aarch64-linux-gnu-', 'CLANG_TRIPLE=aarch64-linux-gnu-',
                'CROSS_COMPILE_ARM32=arm-linux-gnueabi-',
                'GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/', 'HOSTCC=gcc',
                'HOSTCFLAGS=-Wno-error=deprecated-declarations', 'KCFLAGS=-gdwarf-4']
        run(['aarch64-linux-gnu-gcc', '-nostdlib', '-static', '-MD', '-MF', out/'minimal-init.d', '-Wl,--build-id=none',
             '-Wl,-e,_start', ROOT/'note10/device_test/builtin_minimal_init.S',
             '-o', out/'minimal-init.elf'], 'build/00-minimal-init.log')
        init = (out/'minimal-init.elf').read_bytes()
        init_manifest = elf_manifest(init)
        archive_data = cpio(init)
        (out/'initramfs.cpio').write_bytes(archive_data)
        save(out/'minimal-init.json', {'elf': init_manifest,
             'cpio_sha256': hashlib.sha256(archive_data).hexdigest(),
             'cpio_bytes': len(archive_data),
             'members': ['dev', 'dev/console', 'dev/kmsg', 'init', 'TRAILER!!!']})
        settings = dict(SETTINGS, INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"')
        run([*make, DEFCONFIG], 'build/01-defconfig.log')
        shutil.copyfile(objects/'.config', out/'public-baseline.config')
        for index, (name, value) in enumerate(settings.items()):
            if value in ('y', 'n'):
                action = ['--enable' if value == 'y' else '--disable', name]
            elif value.startswith('"'):
                action = ['--set-str', name, value[1:-1]]
            else:
                action = ['--set-val', name, value]
            run([source/'scripts/config', '--file', objects/'.config', *action], f'build/settings/{index:02}.log')
        run([*make, 'olddefconfig'], 'build/02-olddefconfig.log')
        # Preserve the actual effective bytes before any validation can fail.
        shutil.copyfile(objects/'.config', out/'actual-effective.config')
        config = (objects/'.config').read_text().splitlines()
        cmdline_policy = bootloader_cmdline_policy('\n'.join(config))
        for name, value in settings.items():
            wanted = '# CONFIG_'+name+' is not set' if value == 'n' else 'CONFIG_'+name+'='+value
            if wanted not in config and not (value == 'n' and not any(x.startswith('CONFIG_'+name+'=') for x in config)):
                raise ValueError('effective recovery/Image setting differs: '+name)
        # One full new integration target; stock prerequisites are build inputs,
        # not historical test/model/proof executions. No old builder main is called.
        run([*make, 'V=1', '-j'+str(args.jobs), 'Image'], 'build/03-Image.log', timeout=5400)
        capture(source, objects, compiler_include, out)
        retain_route_prerequisites(source, objects, out, compiler_include)
        run(['aarch64-linux-gnu-nm', '-n', objects/TARGET], 'new-object-symbols.log')
        run(['aarch64-linux-gnu-readelf', '-SW', objects/TARGET], 'new-object-sections.log')
        image = objects/'arch/arm64/boot/Image'
        raw = image.read_bytes()
        if len(raw) < 64 or raw[56:60] != b'ARM\x64' or not 0 < struct.unpack_from('<Q', raw, 16)[0] <= 256*1024*1024:
            raise ValueError('completed ARM64 Image header invalid')
        if raw.count(b'N10_CYCLE_SLOT_UNSET_0123456789A') != 1:
            raise ValueError('exact one unpatched inherited recovery cycle slot required')
        if any(marker not in raw for marker in (b'N10RET1', b'N10SHA1', b'N10SHACTL1', b'N10ROUTE2', b'N10INIT2', b'N10MININIT2', b'N10BOOTLINK2', identity.encode())):
            raise ValueError('new diagnostic Image identity/markers missing')
        if raw.count(archive_data) != 1:
            raise ValueError('exact raw builtin CPIO missing/duplicated in actual Image')
        shutil.copyfile(objects/'init/.main.o.cmd', out/'actual-init-main.cmd')
        shutil.copyfile(objects/'init/main.o', out/'init-main.o')
        shutil.copyfile(image, out/'Image')
        shutil.copyfile(objects/'System.map', out/'System.map')
        stable_archive(archive, before)
        if manifest != {name: sha(ROOT/name) for name in manifest}:
            raise ValueError('local first-use inputs changed during build')
        result = dict(schema=1, version='v72', passed=True, kernel_commit=COMMIT,
                      build_evidence_id=identity, ci_context=ci, source_sha256=manifest,
                      settings=settings, make_target='Image', integration_object=TARGET,
                      bootloader_cmdline_policy=cmdline_policy,
                      builtin_init_route=True, minimal_init_elf_sha256=sha(out/'minimal-init.elf'),
                      initramfs_cpio_sha256=sha(out/'initramfs.cpio'),
                      builtin_init_manifest_sha256=sha(out/'minimal-init.json'),
                      guarded_init_main_sha256=sha(source/'init/main.c'),
                      boot_local_identity='get_random_bytes-16-unseeded-strength-not-claimed',
                      image_sha256=sha(image), image_bytes=len(raw), archive_input=before,
                      historical_suites_invoked=0, historical_evaluations_carried_as_executed=0,
                      native_fixture_commands_in_builder=0, kernel_or_provider_executed=False,
                      Image_built=True, BOOT_built=False, cycle_slot_patched=False,
                      recovery_runtime_verified=False, hard_cancellation_proven=False,
                      private_boot_ramdisk_DTB_inputs_used=False,
                      device_authorized=False, deployment_ready=False, device_operations=[])
        result['files_sha256'] = {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()}
        save(out/'result.json', result)
    except Exception as error:
        save(out/'failure.json', {'accepted': False, 'error': repr(error), 'device_operations': []})
        raise


if __name__ == '__main__':
    main()
