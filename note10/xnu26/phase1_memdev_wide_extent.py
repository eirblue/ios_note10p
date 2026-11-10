"""One opt-in patched memdev object in the actual generated BSD context."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from phase1_iostorage_native_inputs import ROOT, command, generate, require, sha


INPUT_PINS = {
    'note10/xnu26/prepare_memdev_wide_extent.py': '7ecb40c0f1371fa79c97b912fbf8e4f7edc641492bbf2e0c6ced1fa40117ede1',
    'note10/xnu26/patches/0014-memdev-wide-byte-extent.patch': '290d38e2fcbd45d7e3d626417e0fa1ba3b8d9b9528a5d511d7cadad9e985f0bc',
    'note10/xnu26/test_memdev_wide_extent.py': 'd82f592347cab7466110c45be57c9cceef949ee63432c91fc1023188c8e22c45',
    'note10/xnu26/test_memdev_wide_extent.c': 'a0e3c8df788810fc89d131c7080bdd14e5303ec2d96d59925d40fc533cd8704b',
    'note10/xnu26/phase1_iostorage_native_inputs.py': 'bf34f56e47bf5a05119ad45d6e00fdd7d6972076aad02f4788459b0c112fa126',
    'note10/xnu26/phase1_iostorage_native_complete.py': 'c6ac1a8685972aabd5eabdf6aa8d66d41e100e895a5212330c77f507f67f3d3c',
    'note10/xnu26/build_native_bootstrap_selection.py': '3cb6f5e2a6d88887597e44a24a5b60e1beeef494cf3b6010b3dea6912d9f5513',
    'note10/xnu26/compile_native_components.py': '0c180519af6099157d5c61a6dda788f23c6ee30dad0c12b5e700336a39a7845c',
    'note10/xnu26/user_instruction_diagnostics.py': 'c703fb7bd72191286dd6e8e4b20176bfe36a0af260e99f2d05c308688e230607',
}
HOST_PASS = {
    'passed': True, 'prepare_attempts': 1, 'compiler_attempts': 1, 'fixture_attempts': 1,
    'cases': 9, 'checks': 31, 'old_tests': 0,
    'result_sha256': 'cafbc2588c32d8f46b987b36a30eb9aefd77e3972bb5621fa55c51b9e14feaca',
    'review_sha256': 'e6c6d2412a92e1d1078dc04909dbb1b59e064e21eaa846858937f3670a367b09',
    'stdout_sha256': '86906543b85096b8fe5e9f61a449463fbaf4ffb36f2277a5108ce66dfed3e28f',
}
DEFINITIONS = ['_mdevBMajor', '_mdevCMajor', '_mdevadd', '_mdevgetrange',
               '_mdevinit', '_mdevlookup', '_mdevremoveall']
PROJECTION_PINS = {
    'note10/xnu26/memdev_config_projection.py': '72fd77f590d47d1612491da9b3f39ccbcca1dca9ac405da27cdd3c855abce563',
    'note10/xnu26/test_memdev_config_projection.py': '72971be9a5560e6aa3088edcabcee33425e895fda477871782e3d66da08499aa',
}


def compile_memdev(result, output, require_arm64_object, *, context_observation=False):
    result.update(passed=False, scope='public-reference-memdev-wide-extent-one-object-no-link-or-runtime',
        stage='memdev-source-binding', host_pass=HOST_PASS, memdev_object_verified=False,
        compiled_arm64_objects=0, target_object_compile_attempts=0, partial_link_attempts=0,
        kernel_links=0, production_hook=False, firmware_abi_verified=False,
        synthetic_board_inputs=True, exact_target_source=False)
    if context_observation:
        result['scope'] = 'public-reference-memdev-context-observation-one-object-no-link-or-runtime'
    pins = dict(INPUT_PINS, **PROJECTION_PINS) if context_observation else INPUT_PINS
    require(all(sha(ROOT / name) == digest for name, digest in pins.items()),
            'reviewed memdev patch or native recipe differs')
    result['source_sha256'].update(pins)
    from prepare_memdev_wide_extent import REL, REFERENCE_PINS, POSTIMAGE_SHA256, PATCH_NAME, PATCH_SHA256, patch_bytes
    from build_native_bootstrap_selection import definitions
    from phase1_iostorage_native_complete import (GENERATION_TOOL_SHA256, GENERATION_HEADER_SHA256,
        PRE_CONFIG_FLAGS, stage_exports)
    from user_instruction_diagnostics import summarize

    generate(result, output)
    result.update(passed=False, stage='memdev-native-context-binding')
    result['generated_header_sha256'] = sorted(row['sha256'] for row in result['fresh_generated_headers'].values())
    require(result['fresh_tool_sha256'] == GENERATION_TOOL_SHA256 and
            {name: row['sha256'] for name, row in result['fresh_generated_headers'].items()} == GENERATION_HEADER_SHA256,
            'accepted native generation tools/headers differ')
    source = output / 'native-work/source'
    context = json.loads((output / 'native-work/context.json').read_bytes())
    compiler = command('xcrun', '-f', 'clang')
    sdk = command('xcrun', '--sdk', 'macosx', '--show-sdk-path')
    require(context['source'] == str(source) and context['compiler'] == compiler and context['sdk'] == sdk and
            context['public_source_commit'] == 'ac9718fb1af618d5ce8678d0dc6e8a58f252216f' and
            context['ci_context']['GITHUB_SHA'] == result['source_head'] and
            context['ci_context']['GITHUB_RUN_ID'] == str(result['run_id']) and
            context['ci_context']['GITHUB_RUN_ATTEMPT'] == '1', 'same-run native context required')
    require(all(sha(source / name) == digest for name, (_, digest) in REFERENCE_PINS.items()),
            'actual memdev declarations differ from accepted host inputs')
    result.update(public_xnu_commit=context['public_source_commit'],
                  public_reference_sha256={name: digest for name, (_, digest) in REFERENCE_PINS.items()})
    native = ROOT / 'note10/private/windows-xnu'
    config = native / 'configured/DEVELOPMENT/bsd'
    if context_observation:
        observation = dict(schema='note10-v169-memdev-context-observation-v1',
                           failure_code='bsd_configuration_record_failed', checks={})
        result['context_observation'] = observation

        def observe(code, checks):
            observation['checks'].update(checks)
            observation['failure_code'] = 'none' if all(checks.values()) else code
            require(all(checks.values()), 'BSD context predicates differ')

    configured = json.loads((native / 'configure-result.json').read_bytes())
    rows = [row for row in configured['configured'] if row['variant'] == 'DEVELOPMENT' and row['component'] == 'bsd']
    if context_observation:
        observe('bsd_configuration_binding_failed', dict(
            bsd_source_directory=configured['source_directory'] == source.relative_to(ROOT).as_posix(),
            bsd_source_commit=configured['source_commit'] == context['public_source_commit'],
            bsd_row_unique=len(rows) == 1,
            bsd_makefile=len(rows) == 1 and (config / 'Makefile').is_file() and
                sha(config / 'Makefile') == rows[0]['makefile_sha256']))
    else:
        require(configured['source_directory'] == source.relative_to(ROOT).as_posix() and
                configured['source_commit'] == context['public_source_commit'] and len(rows) == 1 and
                sha(config / 'Makefile') == rows[0]['makefile_sha256'], 'fresh BSD configuration required')
    if context_observation:
        observation['failure_code'] = 'bsd_headers_read_failed'
    headers = rows[0]['headers']
    if context_observation:
        inventory = type(headers) is dict and 0 < len(headers) <= 512 and 'meta_features.h' in headers
        names = inventory and all(type(name) is str and re.fullmatch(r'[A-Za-z0-9_.+-]{1,96}\.h', name)
                                  for name in headers)
        files = bool(names) and all((config / name).is_file() and
                                   0 < (config / name).stat().st_size <= 1048576 for name in headers)
        hashes = files and all(sha(config / name) == digest for name, digest in headers.items())
        observe('bsd_header_binding_failed', dict(bsd_header_inventory=inventory,
            bsd_header_names=bool(names), bsd_header_files=files, bsd_header_hashes=hashes))
        observation['failure_code'] = 'bsd_defines_parse_failed'
    else:
        require(type(headers) is dict and 0 < len(headers) <= 512 and 'meta_features.h' in headers and
                all(re.fullmatch(r'[A-Za-z0-9_.+-]{1,96}\.h', name) and
                    (config / name).is_file() and 0 < (config / name).stat().st_size <= 1048576 and
                    sha(config / name) == digest for name, digest in headers.items()),
                'all fresh BSD generated headers required')
    defines = definitions((config / 'Makefile').read_text())
    if context_observation:
        observation['checks']['bsd_defines_parsed'] = True
        observation['failure_code'] = 'bsd_defines_projection_failed'
        from memdev_config_projection import project_defines
        public_defines, result['config_projection'] = project_defines(defines)
        observation['checks']['bsd_defines_projected'] = True
        observation['failure_code'] = 'none'
    else:
        require(all(re.fullmatch(r'-D[A-Za-z0-9_]+(?:=[A-Za-z0-9_+.-]+)?', flag) for flag in defines),
                'path-free actual BSD config defines required')
    result.update(bsd_makefile_sha256=rows[0]['makefile_sha256'], bsd_generated_headers_sha256=headers,
        bsd_config_header_sha256=headers['meta_features.h'],
        bsd_config_defines_sha256=hashlib.sha256(json.dumps(defines, separators=(',', ':')).encode()).hexdigest())
    stage_exports(source, native)
    # Match the BSD recipe's actual CoreEntitlements declaration export, not optional KDK trees.
    support = ROOT / 'host-tools/kdk/headers/KDK.pkg/System/Library/KernelSupport'
    support_headers = {}
    for header in sorted((support / 'CoreEntitlements').rglob('*.h')):
        relative = header.relative_to(support)
        require(header.is_file() and 0 < header.stat().st_size <= 1048576 and len(support_headers) < 128,
                'bounded kernel support declarations required')
        destination = native / 'kernel-support-declarations' / relative
        raw = header.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if destination.exists():
            require(sha(destination) == digest, 'existing support declaration differs')
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as stream:
                stream.write(raw)
        support_headers[relative.as_posix()] = digest
    require(support_headers, 'actual BSD kernel support declarations required')
    result['kernel_support_header_sha256'] = support_headers

    result['stage'] = 'memdev-patch-binding'
    patch = ROOT / 'note10/xnu26/patches' / PATCH_NAME
    require(patch_bytes((source / REL).read_bytes()) == patch.read_bytes(), 'exact opt-in patch required')
    result['memdev_source'] = dict(schema='note10-v168-memdev-wide-source-v1',
        source=REL, preimage_sha256=REFERENCE_PINS[REL][1], postimage_sha256=POSTIMAGE_SHA256,
        patch_sha256=PATCH_SHA256, patch_apply_attempts=1, shifted_sites=8, char_count_clamped=True)
    with (output / 'patch.internal.log').open('xb') as log:
        call = subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', str(patch)], cwd=source,
                              stdout=log, stderr=subprocess.STDOUT, timeout=30)
    result['memdev_source']['patch_returncode'] = call.returncode
    require(call.returncode == 0 and sha(source / REL) == POSTIMAGE_SHA256 and
            (source / REL).read_bytes().count(b'(uint64_t)mdev[devid].mdSize << 12') == 8,
            'applied opt-in source differs')

    # Fixed BSD component recipe from compile_native_components; no Mach-private role.
    flags = list(PRE_CONFIG_FLAGS)
    flags[flags.index('-std=gnu++2b')] = '-std=gnu11'
    flags += ['-include', str(config / 'meta_features.h'), *defines, '-isysroot', sdk,
        '-mkernel', '-fno-c++-static-destructors', '-ftrivial-auto-var-init=zero',
        '-fsigned-bitfields', '-fmerge-all-constants', '-fno-strict-aliasing',
        '-momit-leaf-frame-pointer', '-fno-branch-target-identification', '-mno-implicit-sme',
        '-DDRIVER_PRIVATE', '-D_KERNEL_BUILD', '-DKERNEL_BUILD', '-DMACH_KERNEL',
        '-DBSD_BUILD', '-DBSD_KERNEL_PRIVATE', '-DIMAGE4_STRIP_AVAILABILITY=1']
    includes = [native / 'native-link/include', config, native / 'exports', source / 'EXTERNAL_HEADERS',
        native / 'generated-extra/bsd', native / 'generated-extra/bsd', native / 'generated-extra/iokit',
        native / 'native-mig/export/osfmk']
    includes += [native / 'source-exports' / c for c in
        ('bsd', 'osfmk', 'pexpert', 'libkern', 'iokit', 'libsa', 'security', 'san', 'EXTERNAL_HEADERS')]
    includes += [native / 'configured/DEVELOPMENT' / c for c in
        ('osfmk', 'iokit', 'libkern', 'pexpert', 'libsa', 'security', 'san')]
    includes += [source / c for c in ('osfmk', 'bsd', 'pexpert', 'libkern', 'libsa', 'iokit', 'security', 'san', '.')]
    includes += [ROOT / 'host-tools/kdk/headers/KDK_SDK.pkg/System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders/platform',
        native / 'kernel-support-declarations', ROOT / 'host-tools/opensource-declarations']
    includes += [Path(sdk) / p for p in ('System/Library/Frameworks/Kernel.framework/Versions/A/Headers',
        'System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders',
        'System/Library/Frameworks/Kernel.framework/Headers', 'System/Library/Frameworks/Kernel.framework/PrivateHeaders',
        'usr/local/include', 'usr/include')]
    for path in includes:
        flags += ['-I', str(path)]
    obj = output / 'memdev-wide.o'
    argv = [compiler, *flags, '-c', str(source / REL), '-o', str(obj)]
    require(not any(flag == '-DMACH_KERNEL_PRIVATE' or flag.startswith('-DMACH_KERNEL_PRIVATE=')
                    for flag in argv), 'actual BSD component role required')
    with (output / 'compiler-argv.internal.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(argv) + '\n')
    path_options = {'-I', '-include', '-isysroot', '-c', '-o'}
    safe_flags = [arg for i, arg in enumerate(argv[1:], 1) if arg not in path_options and argv[i-1] not in path_options]
    if context_observation:
        safe_flags = [*safe_flags[:len(PRE_CONFIG_FLAGS)], *public_defines,
                      *safe_flags[len(PRE_CONFIG_FLAGS) + len(defines):]]
    result.update(stage='memdev-one-object-compile', compiler_flags=safe_flags, compiler_argv_count=len(argv),
        compiler_argv_sha256=hashlib.sha256(json.dumps(argv, separators=(',', ':')).encode()).hexdigest(),
        compile_attempts=1, target_object_compile_attempts=1)
    roots = {str(ROOT / 'note10/xnu26'): 'port', str(source): 'XNU', str(native): 'generated',
             sdk: 'SDK', str(output): 'output', compiler: 'compiler'}
    try:
        call = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired as error:
        result.update(compiler_timed_out=True, compiler_diagnostics=summarize(error.stderr or b'', roots))
        (output / 'compiler.internal.log').write_bytes((error.stdout or b'') + (error.stderr or b''))
        raise
    result.update(compiler_returncode=call.returncode, compiler_diagnostics=summarize(call.stderr, roots))
    (output / 'compiler.internal.log').write_bytes(call.stdout + call.stderr)
    if call.returncode:
        return
    result['stage'] = 'memdev-object-audit'
    require_arm64_object(obj)
    result.update(compiled_arm64_objects=1, object_sha256=sha(obj), object_bytes=obj.stat().st_size)
    defined = command('xcrun', '--sdk', 'macosx', 'nm', '-g', '-U', '-j', str(obj)).splitlines()
    undefined = command('xcrun', '--sdk', 'macosx', 'nm', '-u', '-j', str(obj)).splitlines()
    require(len(defined) <= 32 and len(undefined) <= 256 and
            all(re.fullmatch(r'[A-Za-z_.$][A-Za-z0-9_.$]{0,383}', name) for name in defined + undefined) and
            len(set(defined)) == len(defined) and len(set(undefined)) == len(undefined),
            'bounded actual object symbol metadata required')
    result.update(defined_external_symbols=sorted(defined), undefined_external_symbols=sorted(undefined))
    require(sorted(defined) == DEFINITIONS, 'unexpected memdev global definitions')
    result.update(stage='complete', passed=True, memdev_object_verified=True)
