"""New recovery/KAT diagnostic Image; no old suites, packaging or device actions."""
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
    'note10/device_test/sha256_kat_recovery.c',
    'note10/device_test/sha256_kat_recovery_work.c',
    'note10/device_test/prepare_sha256_kat_recovery.py',
    'note10/device_test/build_sha256_kat_recovery.py',
    'note10/device_test/test_sha256_kat_recovery.py',
    'note10/device_test/sha256_kat_recovery_fixture.c',
    '.github/workflows/note10-sha256-kat-recovery.yml',
)
INPUTS = (
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
    'NOTE10_SHA256_KAT_RECOVERY': 'y',
    'CRYPTO': 'y', 'CRYPTO_HASH': 'y', 'CRYPTO_SHA256': 'y',
    'EXYNOS_REBOOT': 'y', 'SEC_REBOOT': 'y', 'BLK_DEV_INITRD': 'y',
    'INITRAMFS_SOURCE': '""', 'INITRAMFS_FORCE': 'n',
    'CMDLINE': '""', 'CMDLINE_FORCE': 'n', 'CMDLINE_FROM_BOOTLOADER': 'n',
    'CMDLINE_EXTEND': 'y', 'LOG_BUF_SHIFT': '21',
    'LTO': 'n', 'LTO_CLANG': 'n', 'FTRACE_MCOUNT_RECORD': 'n',
    'STACK_VALIDATION': 'n', 'LOCALVERSION_AUTO': 'n',
    'LOCALVERSION': '"-v71-sha256-recovery"',
}
BUILD_INPUT_PINS = {
    'firmware/Makefile': 'd25d7ed1b358b79841dab8ce18fc03d799e9bac4609b6ef37e4c32bec8f6a47c',
    'init/initramfs.c': '1a9af19668584dc664c28c640e02b6a03cc37a2fa5ecd1900d818bb67c775806',
}


def prepare_image_inputs(source):
    """The existing full builder's two source transforms, without its main/tests."""
    for name, expected in BUILD_INPUT_PINS.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest() != expected:
            raise ValueError('pinned Image input changed: '+name)
    firmware = source/'firmware/Makefile'
    old = '$(call cmd,fwbin,$(patsubst %.gen.S,%,$@))'
    new = '$(call cmd,fwbin,$(if $(wildcard $(srctree)/$(patsubst %.gen.S,%,$@)),$(srctree)/$(patsubst %.gen.S,%,$@),$(patsubst %.gen.S,%,$@)))'
    initrd = source/'init/initramfs.c'
    skip = '\tdo_skip_initramfs = 1;'
    if firmware.read_text().count(old) != 1 or initrd.read_text().count(skip) != 1:
        raise ValueError('unexpected existing Image preparation anchors')
    firmware.write_text(firmware.read_text().replace(old, new))
    initrd.write_text(initrd.read_text().replace(skip,
                     '\tpr_info("N10CAP1: keeping diagnostic initramfs\\n");'))
    return {name: hashlib.sha256((source/name).read_bytes()).hexdigest() for name in BUILD_INPUT_PINS}


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
    from prepare_sha256_kat_recovery import install, TARGET, KERNEL_PINS
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
        for name in (*KERNEL_PINS, *BUILD_INPUT_PINS):
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
        run([*make, DEFCONFIG], 'build/01-defconfig.log')
        shutil.copyfile(objects/'.config', out/'public-baseline.config')
        for index, (name, value) in enumerate(SETTINGS.items()):
            if value in ('y', 'n'):
                action = ['--enable' if value == 'y' else '--disable', name]
            elif value.startswith('"'):
                action = ['--set-str', name, value[1:-1]]
            else:
                action = ['--set-val', name, value]
            run([source/'scripts/config', '--file', objects/'.config', *action], f'build/settings/{index:02}.log')
        run([*make, 'olddefconfig'], 'build/02-olddefconfig.log')
        config = (objects/'.config').read_text().splitlines()
        for name, value in SETTINGS.items():
            wanted = '# CONFIG_'+name+' is not set' if value == 'n' else 'CONFIG_'+name+'='+value
            if wanted not in config and not (value == 'n' and not any(x.startswith('CONFIG_'+name+'=') for x in config)):
                raise ValueError('effective recovery/Image setting differs: '+name)
        # One full new integration target; stock prerequisites are build inputs,
        # not historical test/model/proof executions. No old builder main is called.
        run([*make, 'V=1', '-j'+str(args.jobs), 'Image'], 'build/03-Image.log', timeout=5400)
        capture(source, objects, compiler_include, out)
        run(['aarch64-linux-gnu-nm', '-n', objects/TARGET], 'new-object-symbols.log')
        run(['aarch64-linux-gnu-readelf', '-SW', objects/TARGET], 'new-object-sections.log')
        image = objects/'arch/arm64/boot/Image'
        raw = image.read_bytes()
        if len(raw) < 64 or raw[56:60] != b'ARM\x64' or not 0 < struct.unpack_from('<Q', raw, 16)[0] <= 256*1024*1024:
            raise ValueError('completed ARM64 Image header invalid')
        if raw.count(b'N10_CYCLE_SLOT_UNSET_0123456789A') != 1:
            raise ValueError('exact one unpatched inherited recovery cycle slot required')
        if any(marker not in raw for marker in (b'N10RET1', b'N10SHA1', b'N10SHACTL1', identity.encode())):
            raise ValueError('new diagnostic Image identity/markers missing')
        shutil.copyfile(image, out/'Image')
        shutil.copyfile(objects/'System.map', out/'System.map')
        stable_archive(archive, before)
        if manifest != {name: sha(ROOT/name) for name in manifest}:
            raise ValueError('local first-use inputs changed during build')
        result = dict(schema=1, version='v71', passed=True, kernel_commit=COMMIT,
                      build_evidence_id=identity, ci_context=ci, source_sha256=manifest,
                      settings=SETTINGS, make_target='Image', integration_object=TARGET,
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
