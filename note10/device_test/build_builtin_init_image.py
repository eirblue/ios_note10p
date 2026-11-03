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
    'CMDLINE': '"rdinit=/init"', 'CMDLINE_FORCE': 'n', 'CMDLINE_EXTEND': 'y',
    'CMDLINE_FROM_BOOTLOADER': 'n', 'LOG_BUF_SHIFT': '21',
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


def main(kind=None):
    if kind not in (None, "sha256-stream-state", "cpu-affinity-binding", "early-fdt-binding", "native-memory-observation", "linux-data-carrier", "owned-contiguous-staging-pc", "current-owned-staging-pc", "readonly-input-pc", "kernel-readonly-candidate"):
        raise ValueError("closed diagnostic task required")
    kernel_ro = kind == "kernel-readonly-candidate"
    readonly = kind == "readonly-input-pc"
    stream = kind == "sha256-stream-state"
    affinity = kind == "cpu-affinity-binding"
    fdt = kind == "early-fdt-binding"
    native = kind == "native-memory-observation"
    current_owned = kind == "current-owned-staging-pc"
    owned = kind in ("owned-contiguous-staging-pc","current-owned-staging-pc")
    data_task = kind in ("linux-data-carrier","owned-contiguous-staging-pc","current-owned-staging-pc","readonly-input-pc","kernel-readonly-candidate")
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
    extra = ('sha256_stream_state.py', 'sha256_stream_state.c', 'sha256_stream_composition.c',
             'sha256_stream_vectors.json', 'build_sha256_stream_state.py',
             'test_sha256_stream_state.py', 'sha256_stream_fixture.c') if stream else (
             'affinity_binding.py', 'cpu_affinity_binding.c', 'affinity_binding_composition.c',
             'build_cpu_affinity_binding.py', 'test_affinity_binding.py', 'sealed_affinity_artifact.cjs',
             'bundle_affinity_evidence.py') if affinity else (
             'early_fdt_binding.py', 'early_fdt_binding.c', 'early_fdt_composition.c',
             'build_early_fdt_binding.py', 'test_early_fdt_binding.py', 'early_fdt_fixture.c',
             'sealed_affinity_artifact.cjs', 'bundle_affinity_evidence.py') if fdt else (
             'native_memory_observation.py','native_memory_observation.c','native_memory_composition.c',
             'build_native_memory_observation.py','test_native_memory_observation.py','native_memory_fixture.c',
             'early_fdt_binding.py','sealed_affinity_artifact.cjs','bundle_affinity_evidence.py') if native else (
             'linux_data_carrier.py','linux_data_carrier.c','linux_data_carrier_composition.c',
             'build_linux_data_carrier.py','linux_data_carrier_fixture.c','test_linux_data_carrier.py',
             'carrier_lzma.c','carrier_lzma.h','linux_data_compare_evidence.h',
             'linux_data_input_probe_fixture.c','test_v100_carrier_input_probe.py',
             'linux_data_input_range.h','linux_data_input_range_fixture.c','test_v101_live_input_range.py',
             'linux_data_early_prefix.h','linux_data_early_prefix_fixture.c','test_v102_input_lifetime.py',
             'linux_data_growth.h','linux_data_growth_fixture.c','test_v104_growth_region.py',
             'early_fdt_binding.py','sealed_affinity_artifact.cjs',
             'bundle_affinity_evidence.py') if data_task else ()
    if kernel_ro:
        from kernel_readonly_input import SOURCES as kernel_ro_sources
        extra=(*extra,*kernel_ro_sources)
    if readonly:
        from readonly_input_pc import SOURCES as readonly_sources
        extra=(*extra,*readonly_sources)
    if owned:
        extra=(*extra,'owned_contiguous_staging.py','owned_contiguous_staging.c','owned_contiguous_staging_composition.c',
               'build_owned_contiguous_staging.py','test_owned_contiguous_staging.py')
    if current_owned:
        extra=(*extra,'current_owned_staging.py','current_owned_capacity.h','current_owned_staging_composition.c',
               'build_current_owned_staging.py','current_owned_staging_fixture.c','test_current_owned_staging.py')
    names = (*PUBLIC, *INPUTS, *('note10/device_test/'+n for n in extra),
             *(('.github/workflows/note10-sha256-stream-state.yml',) if stream else
               ('.github/workflows/note10-cpu-affinity-binding.yml',) if affinity else
               ('.github/workflows/note10-early-fdt-binding.yml',) if fdt else
               ('.github/workflows/note10-native-memory-observation.yml',) if native else
               ('.github/workflows/note10-current-owned-staging-pc.yml',) if current_owned else
               ('.github/workflows/note10-owned-contiguous-staging-pc.yml',) if owned else
               ('.github/workflows/note10-linux-data-carrier.yml',) if data_task else ()))
    for name in names:
        data = (ROOT/name).read_bytes()
        manifest[name] = hashlib.sha256(data).hexdigest()
        target = out/'source'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    from build_sha256_runtime_kat import sha, save, capture
    from build_xnu_runtime_plan_component import acquire, extract, COMMIT, DEFCONFIG
    from pre_pm_archive_contract import archive_identity, stable_archive
    from prepare_sha256_kat_recovery import TARGET, KERNEL_PINS
    from builtin_init_route import install, API_PINS, elf_manifest, cpio, builtin_cmdline_policy
    from build_sha256_kat_recovery import BUILD_INPUT_PINS, prepare_image_inputs
    extra_kernel_pins = {}
    if stream:
        from sha256_stream_state import install, API_PINS as extra_kernel_pins
    elif affinity:
        from affinity_binding import install, API_PINS as extra_kernel_pins
    elif fdt:
        from early_fdt_binding import install, API_PINS as extra_kernel_pins
    elif native:
        from native_memory_observation import install, API_PINS as extra_kernel_pins
    elif kernel_ro:
        from kernel_readonly_input import install, API_PINS as extra_kernel_pins
    elif readonly:
        from readonly_input_pc import install, API_PINS as extra_kernel_pins
    elif current_owned:
        from current_owned_staging import install, API_PINS as extra_kernel_pins
    elif owned:
        from owned_contiguous_staging import install, API_PINS as extra_kernel_pins
    elif data_task:
        from linux_data_carrier import install, API_PINS as extra_kernel_pins
    save(out/'source-manifest.json', manifest)
    ci = {name: os.environ.get(name) for name in
          ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB')}
    if current_owned or readonly or kernel_ro:
        ci.update({name:os.environ.get(name) for name in ('GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA','GITHUB_REPOSITORY')})
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
        for name in (*KERNEL_PINS, *BUILD_INPUT_PINS, *API_PINS, *extra_kernel_pins, "usr/Kconfig", "include/linux/sched.h"):
            target = out/'stock-inputs'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source/name, target)
        # Diagnostic hooks follow the existing original-input preparation.
        image_prep = prepare_image_inputs(source) if (fdt or native or data_task) else None
        overlay = install(source, identity)
        if not (fdt or native or data_task):
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
        if stream:
            settings.update(NOTE10_SHA256_STREAM_STATE='y', LOCALVERSION='"-v73-sha256-stream"')
        elif affinity:
            settings.update(NOTE10_CPU_AFFINITY_BINDING='y', NOTE10_SHA256_STREAM_STATE='n',
                            SMP='y', LOCALVERSION='"-v78-cpu-affinity"')
        elif fdt:
            settings.update(NOTE10_EARLY_FDT_BINDING='y', NOTE10_CPU_AFFINITY_BINDING='n',
                            NOTE10_SHA256_STREAM_STATE='n', HAVE_MEMBLOCK='y', NO_BOOTMEM='y',
                            SMP='y', LOCALVERSION='"-v81-early-fdt"')
        elif native:
            settings.update(NOTE10_NATIVE_MEMORY_OBSERVATION='y',NOTE10_EARLY_FDT_BINDING='n',
                            NOTE10_CPU_AFFINITY_BINDING='n',NOTE10_SHA256_STREAM_STATE='n',
                            SMP='y',LOCALVERSION='"-v82-native-memory"')
        elif data_task:
            settings.update(NOTE10_DATA_CARRIER='y', NOTE10_NATIVE_MEMORY_OBSERVATION='n',
                            NOTE10_EARLY_FDT_BINDING='n', NOTE10_CPU_AFFINITY_BINDING='n',
                            NOTE10_SHA256_STREAM_STATE='n', SMP='y', LOCALVERSION='"-v91-trusted-logical"')
        if kernel_ro:
            settings.update(NOTE10_KERNEL_READONLY_INPUT='y',NOTE10_READONLY_INPUT_PC='n',LOCALVERSION='"-v105-kernel-readonly"')
        if readonly:
            settings.update(NOTE10_READONLY_INPUT_PC='y',LOCALVERSION='"-v103-readonly-input-pc"')
        if owned:
            settings.update(NOTE10_OWNED_CONTIGUOUS_STAGING='y',HAVE_MEMBLOCK='y',NO_BOOTMEM='y',LOCALVERSION='"-v92-owned-contiguous-pc"')
        if current_owned:
            settings.update(NOTE10_CURRENT_OWNED_STAGING='y',LOCALVERSION='"-v96-current-owned-pc"')
        if data_task and not owned and not readonly:
            settings.update(NOTE10_READONLY_INPUT_PC='n')
        if data_task and not owned:
            settings.update(NOTE10_OWNED_CONTIGUOUS_STAGING='n', NOTE10_CURRENT_OWNED_STAGING='n')
        run([*make, DEFCONFIG], 'build/01-defconfig.log')
        owned_default_enabled=owned and any(line.startswith('CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING=') for line in (objects/'.config').read_text().splitlines())
        if owned_default_enabled:
            raise ValueError('owned staging must be disabled in unchanged baseline config')
        current_owned_default_enabled=current_owned and any(line.startswith('CONFIG_NOTE10_CURRENT_OWNED_STAGING=') for line in (objects/'.config').read_text().splitlines())
        if current_owned_default_enabled:
            raise ValueError('current owned staging must be default off')
        readonly_default_enabled=readonly and any(line.startswith('CONFIG_NOTE10_READONLY_INPUT_PC=') for line in (objects/'.config').read_text().splitlines())
        if readonly_default_enabled:
            raise ValueError('readonly input must be default off')
        kernel_ro_default_enabled=kernel_ro and any(line.startswith('CONFIG_NOTE10_KERNEL_READONLY_INPUT=') for line in (objects/'.config').read_text().splitlines())
        if kernel_ro_default_enabled:
            raise ValueError('kernel readonly candidate must be default off')
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
        cmdline_policy = builtin_cmdline_policy('\n'.join(config))
        for name, value in settings.items():
            wanted = '# CONFIG_'+name+' is not set' if value == 'n' else 'CONFIG_'+name+'='+value
            if wanted not in config and not (value == 'n' and not any(x.startswith('CONFIG_'+name+'=') for x in config)):
                raise ValueError('effective recovery/Image setting differs: '+name)
        # One full new integration target; stock prerequisites are build inputs,
        # not historical test/model/proof executions. No old builder main is called.
        run([*make, 'V=1', '-j'+str(args.jobs), 'Image'], 'build/03-Image.log', timeout=5400)
        capture(source, objects, compiler_include, out)
        retain_route_prerequisites(source, objects, out, compiler_include)
        run(['aarch64-linux-gnu-nm', *(['-S'] if (fdt or native or data_task) else []), '-n', objects/TARGET], 'new-object-symbols.log')
        run(['aarch64-linux-gnu-readelf', '-SW', objects/TARGET], 'new-object-sections.log')
        if readonly or kernel_ro:
            run(['aarch64-linux-gnu-readelf','-sW',objects/TARGET],'new-object-symbol-table.log')
        image = objects/'arch/arm64/boot/Image'
        raw = image.read_bytes()
        if len(raw) < 64 or raw[56:60] != b'ARM\x64' or not 0 < struct.unpack_from('<Q', raw, 16)[0] <= 256*1024*1024:
            raise ValueError('completed ARM64 Image header invalid')
        if raw.count(b'N10_CYCLE_SLOT_UNSET_0123456789A') != 1:
            raise ValueError('exact one unpatched inherited recovery cycle slot required')
        if any(marker not in raw for marker in (b'N10RET1', b'N10DATARO1' if kernel_ro else b'N10DATAPC1' if readonly else b'N10DATA1' if data_task else b'N10MEMARGS1' if native else b'N10FDT1' if fdt else b'N10AFF1' if affinity else b'N10SHASTREAM1' if stream else b'N10SHA1', b'N10SHACTL1', b'N10ROUTE2', b'N10INIT2', b'N10MININIT2', b'N10BOOTLINK2', identity.encode())):
            raise ValueError('new diagnostic Image identity/markers missing')
        if (stream and b'N10SHA1' in raw) or ((affinity or fdt) and any(marker in raw for marker in (b'N10SHA1', b'N10SHASTREAM1'))) or (fdt and b'N10AFF1' in raw) or (native and any(marker in raw for marker in (b'N10SHA1',b'N10SHASTREAM1',b'N10AFF1',b'N10FDT1'))):
            raise ValueError('old SHA tasks must not be compiled into the new task')
        if data_task and any(marker in raw for marker in (b'N10SHA1',b'N10SHASTREAM1',b'N10AFF1',b'N10FDT1',b'N10MEMARGS1')):
            raise ValueError('old diagnostic callback compiled into DATA task')
        normal_readonly_excluded=False
        if data_task and not owned and not readonly and not kernel_ro:
            if ('CONFIG_NOTE10_READONLY_INPUT_PC=y' in config or b'N10ROINPUTPCV1!!' in raw or
                'n10_readonly_input' in (out/'new-object-symbols.log').read_text() or
                'n10_readonly_descriptor' in (out/'new-object-symbols.log').read_text() or
                '.rodata.n10_readonly_' in (out/'new-object-sections.log').read_text()):
                raise ValueError('small normal DATA must not contain readonly PC slot')
            normal_readonly_excluded=True
        if raw.count(archive_data) != 1:
            raise ValueError('exact raw builtin CPIO missing/duplicated in actual Image')
        shutil.copyfile(objects/'init/.main.o.cmd', out/'actual-init-main.cmd')
        shutil.copyfile(objects/'init/main.o', out/'init-main.o')
        shutil.copyfile(image, out/'Image')
        shutil.copyfile(objects/'System.map', out/'System.map')
        stable_archive(archive, before)
        if manifest != {name: sha(ROOT/name) for name in manifest}:
            raise ValueError('local first-use inputs changed during build')
        result = dict(schema=1, version='v105' if kernel_ro else 'v103' if readonly else 'v96' if current_owned else 'v92' if owned else 'v91' if data_task else 'v82' if native else 'v81' if fdt else 'v78' if affinity else 'v73' if stream else 'v72', diagnostic_kind=kind, passed=True, kernel_commit=COMMIT,
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
        if affinity:
            result.update(raw_input_binding=False, original_fdt_digest_unavailable=True)
        if fdt:
            from early_fdt_binding import linked_footprint, relative_placement_admission, CAPACITY, BOUNDARY, REVISION, ALLOCATION
            footprint = linked_footprint((objects/'System.map').read_text(),
                (out/'new-object-symbols.log').read_text(), struct.unpack_from('<Q',raw,16)[0],
                struct.unpack_from('<Q',raw,8)[0],struct.unpack_from('<Q',raw,24)[0])
            result.update(raw_input_binding=False, fdt_capture_boundary=BOUNDARY,
                          fdt_snapshot_capacity_bytes=CAPACITY, fdt_snapshot_footprint=footprint,
                          fdt_capture_revision=REVISION,fdt_allocation_form=ALLOCATION,
                          physical_placement_review_required=True)
            result['fdt_relative_placement']=relative_placement_admission(result,config,footprint)
        if native:
            from native_memory_observation import linked_footprint,relative_admission,STAGE,CAPACITY
            footprint=linked_footprint((objects/'System.map').read_text(),(out/'new-object-symbols.log').read_text(),
                struct.unpack_from('<Q',raw,16)[0],struct.unpack_from('<Q',raw,8)[0],struct.unpack_from('<Q',raw,24)[0])
            result.update(raw_input_binding=False,native_memory_stage=STAGE,native_memory_capacity=CAPACITY,
                native_memory_footprint=footprint,physical_placement_review_required=True)
            result['files_sha256']={'minimal-init.elf':result['minimal_init_elf_sha256'],
                                    'initramfs.cpio':result['initramfs_cpio_sha256']}
            result['native_relative_placement']=relative_admission(result,config,footprint,elf=init,archive=archive_data,
                raw_inputs={k:result[k] for k in ('minimal_init_elf_sha256','initramfs_cpio_sha256')})
        if data_task and not readonly and not kernel_ro:
            from linux_data_carrier import linked_footprint, relative_admission, STAGE, MODE, slot_metadata
            footprint = linked_footprint((objects/'System.map').read_text(),(out/'new-object-symbols.log').read_text(),
                struct.unpack_from('<Q',raw,16)[0],struct.unpack_from('<Q',raw,8)[0],struct.unpack_from('<Q',raw,24)[0])
            slot = slot_metadata(raw,(objects/'System.map').read_text(),(out/'new-object-symbols.log').read_text(),(out/'new-object-sections.log').read_text())
            result.update(raw_input_binding=False,data_carrier_stage=STAGE,data_footprint=footprint,physical_placement_review_required=True,
                          data_expectation_mode=MODE,data_expectation_slot=slot,image_expectation_patched=False)
            if not owned:
                from linux_data_carrier import COMPARE_SCHEMA, RANGE_SCHEMA, EARLY_SCHEMA, GROWTH_BINDING, growth_declaration
                result['data_compare_schema'] = COMPARE_SCHEMA
                result.update(data_input_range_schema=RANGE_SCHEMA,data_linked_kernel_bytes=footprint['linked_kernel_bytes'])
                result['data_early_prefix_schema']=EARLY_SCHEMA
                result.update(GROWTH_BINDING,readonly_PC_disabled=normal_readonly_excluded,
                    readonly_input_slot_absent=normal_readonly_excluded)
                growth_declaration(result)
            result['files_sha256'] = {'minimal-init.elf':result['minimal_init_elf_sha256'],'initramfs.cpio':result['initramfs_cpio_sha256']}
            data_config=[x for x in config if not x.startswith(('CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING=','CONFIG_NOTE10_CURRENT_OWNED_STAGING=')) and x not in ('# CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING is not set','# CONFIG_NOTE10_CURRENT_OWNED_STAGING is not set')] if owned else config
            result['data_relative_placement'] = relative_admission(result,data_config,footprint,elf=init,archive=archive_data,
                raw_inputs={k:result[k] for k in ('minimal_init_elf_sha256','initramfs_cpio_sha256')})
        if owned:
            if current_owned:
                from current_owned_staging import footprint as owned_footprint, relative as owned_relative, pc_contract, BYTES, ALIGN
            else:
                from owned_contiguous_staging import footprint as owned_footprint, relative as owned_relative, pc_contract, BYTES, ALIGN
            record=owned_footprint((objects/'System.map').read_text(),(out/'new-object-symbols.log').read_text(),
                struct.unpack_from('<Q',raw,16)[0],struct.unpack_from('<Q',raw,8)[0],struct.unpack_from('<Q',raw,24)[0])
            result.update(PC_only=True,physical_ready=False,owned_capacity_bytes=BYTES,owned_alignment_bytes=ALIGN,
                owned_default_enabled=owned_default_enabled,owned_footprint=record,
                owned_relative_placement=owned_relative(result,config,record,elf=init,archive=archive_data,
                    raw_inputs={k:result[k] for k in ('minimal_init_elf_sha256','initramfs_cpio_sha256')}))
            if current_owned:
                result.update(current_owned_default_enabled=current_owned_default_enabled,owned_capacity_source='current_owned_capacity.h')
            result['owned_pc_contract']=pc_contract(result,os.environ.get('GITHUB_SHA',''))
        if readonly:
            from readonly_input_pc import slot_metadata as readonly_metadata, pc_contract, MODE as readonly_mode, SCHEMA as readonly_schema, CAPACITY, DESCRIPTOR_BYTES
            from linux_data_carrier import linked_footprint
            record=readonly_metadata(raw,(objects/'System.map').read_text(),
                (out/'new-object-symbols.log').read_text(),(out/'new-object-sections.log').read_text(),
                (out/'new-object-symbol-table.log').read_text())
            footprint=linked_footprint((objects/'System.map').read_text(),(out/'new-object-symbols.log').read_text(),
                struct.unpack_from('<Q',raw,16)[0],struct.unpack_from('<Q',raw,8)[0],struct.unpack_from('<Q',raw,24)[0])
            result.update(PC_only=True,physical_ready=False,readonly_input_schema=readonly_schema,
                readonly_input_slot=record,readonly_default_enabled=readonly_default_enabled,
                data_expectation_mode=readonly_mode,data_footprint=footprint,
                permanent_input_storage_bytes=CAPACITY,permanent_descriptor_bytes=DESCRIPTOR_BYTES,
                input_capture_source='late-kernel-readonly-slot-only',external_initrd_capture=False,
                physical_placement_review_required=True,global_RAM_ownership=False,
                additional_linked_storage_bytes=CAPACITY+DESCRIPTOR_BYTES,
                readonly_storage_growth=dict(added_input_bytes=CAPACITY,added_descriptor_bytes=DESCRIPTOR_BYTES,
                    actual_image_file_bytes=len(raw),actual_linked_kernel_bytes=footprint['linked_kernel_bytes'],
                    exact_growth_vs_saved_current='Root JSON-only comparison; no baseline build or placement claim'))
            result['readonly_pc_contract']=pc_contract(result,os.environ.get('GITHUB_SHA',''))
        if kernel_ro:
            from kernel_readonly_input import slot_metadata as kro_metadata, producer_contract, MODE as kro_mode, SCHEMA as kro_schema, KIND as kro_kind, CAPACITY, BUDGET
            from linux_data_carrier import linked_footprint
            record=kro_metadata(raw,(objects/'System.map').read_text(),(out/'new-object-symbols.log').read_text(),
                (out/'new-object-sections.log').read_text(),(out/'new-object-symbol-table.log').read_text())
            footprint=linked_footprint((objects/'System.map').read_text(),(out/'new-object-symbols.log').read_text(),
                struct.unpack_from('<Q',raw,16)[0],struct.unpack_from('<Q',raw,8)[0],struct.unpack_from('<Q',raw,24)[0])
            if footprint['linked_kernel_bytes']>BUDGET:
                raise ValueError('actual readonly candidate exceeds explicit linked budget')
            result.update(PC_only=False,physical_ready=False,data_input_kind=kro_kind,kernel_readonly_schema=kro_schema,
                kernel_readonly_slot=record,kernel_readonly_linked_bytes=footprint['linked_kernel_bytes'],kernel_readonly_image_bytes=len(raw),
                kernel_readonly_requires_ack=True,kernel_readonly_default_enabled=kernel_ro_default_enabled,
                data_expectation_mode=kro_mode,data_expectation_slot=record,image_expectation_patched=False,data_footprint=footprint,
                external_initrd_capture=False,input_capture_source='late-kernel-readonly-class2',
                permanent_input_storage_bytes=CAPACITY,permanent_descriptor_bytes=80,additional_linked_storage_bytes=CAPACITY+80,
                physical_placement_review_required=True,requires_new_user_growth_scope=True,global_RAM_ownership=False)
            result['kernel_readonly_candidate_contract']=producer_contract(result,os.environ.get('GITHUB_SHA',''))
        result['files_sha256'] = {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()}
        save(out/'result.json', result)
    except Exception as error:
        save(out/'failure.json', {'accepted': False, 'error': repr(error), 'device_operations': []})
        raise


if __name__ == '__main__':
    main()
