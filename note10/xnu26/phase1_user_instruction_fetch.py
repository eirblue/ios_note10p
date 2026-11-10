"""Compile one reviewed user-fetch object in the retained native XNU context."""
import hashlib
import json
import re
import subprocess

from phase1_iostorage_native_inputs import ROOT, command, generate, require, sha


SOURCE = 'note10/xnu26/note10_user_instruction_fetch.c'
HEADER = 'note10/xnu26/note10_user_instruction_fetch.h'
HOST_RECIPE = 'note10/xnu26/test_user_instruction_fetch.py'
INPUT_PINS = {
    SOURCE: '20becc0643449b8116a22efb377e9486c18830569e5294c87931930d004eb1b3',
    HEADER: '6a9817830b75296d59f087b2cf96e872c8f9d4018b51e5b16d6e3b3cfdc96238',
    HOST_RECIPE: '23d32905dc66fb23a9ee34cfeba0689165302114bf8552b1bda0381005975f25',
    'note10/xnu26/phase1_iostorage_native_inputs.py': 'bf34f56e47bf5a05119ad45d6e00fdd7d6972076aad02f4788459b0c112fa126',
    'note10/xnu26/phase1_iostorage_native_complete.py': 'd383b7192f040ac860bb36032ab94828c48354ea2dda444d1357fd96cb5cc994',
    'note10/xnu26/compile_native_components.py': '0c180519af6099157d5c61a6dda788f23c6ee30dad0c12b5e700336a39a7845c',
}
HOST_PASS = {
    'status': 'pass',
    'cases': 16, 'prepare_attempts': 1, 'compiler_attempts': 1, 'fixture_attempts': 1,
    'reservation_sha256': 'ddd3b2570f4e7956888f627c2710a03dbc59482866272cddf7fbabfc71cb18c6',
    'fixture_log_sha256': '1115a35be7d00025ef6af8a218fa9e4fcdfa150c70a5ab5dcae2dcddccd668cf',
    'coding_receipt_sha256': 'efa5adca7b44c4698210727d1d0465900872924e8fba9a4802bc1d74342a1e23',
}
# The retained board patch adds cache-line definitions, not a saved-state ABI.
NATIVE_PROC_REG_SHA256 = 'a50f2a60a6a96c536cf2ee91a1b55e50cd70063280abc828c5900e9eba989fef'
DIAGNOSTIC_PINS = {
    'note10/xnu26/user_instruction_diagnostics.py': 'c703fb7bd72191286dd6e8e4b20176bfe36a0af260e99f2d05c308688e230607',
    'note10/xnu26/test_user_instruction_diagnostics.py': '9ced29a56abea6a2c0a0d25e60af77e129eb2b82d602bc3f89b1d4adea86dfb5',
}
CONTEXT_HEADER = 'note10/xnu26/user_instruction_header_context.h'
CONTEXT_HEADER_SHA256 = 'a2fa27027f150b5b76168f3c025287697e383225063d80b951973e0cc41ef069'
CONTEXT_REFERENCE_PINS = {
    'bsd/sys/types.h': 'f8b136bb10d56bb604e7b253f1ec23858d0b4ae21fe85eaede0ccc66afdb554a',
    'bsd/sys/_types.h': '508393c2752392fb306f3f9540f848e766f9bb4b52a5f616739a9cc63006f9ec',
    'bsd/sys/_types/_dev_t.h': '4ba3d19759544b9f7bf424d2a16a518ff586e31ed968d525440e678cfbb07a5d',
    'osfmk/libsa/string.h': '630b7c4668cd1ed1995fd6b3fc4a1e1f33d592f1bb100f4c6a00e58a819fb514',
}


def compile_object(result, output, require_arm64_object, *, diagnostics=False, header_context=False):
    result.update(passed=False, stage='user-fetch-source-binding', host_pass=HOST_PASS,
                  scope='public-reference-native-user-fetch-one-object-no-link-or-runtime',
                  user_instruction_object_verified=False, compiled_arm64_objects=0,
                  partial_link_attempts=0, target_object_compile_attempts=0,
                  kernel_links=0, production_hook=False, firmware_abi_verified=False,
                  synthetic_board_inputs=True, exact_target_source=False)
    require(all(sha(ROOT / name) == digest for name, digest in INPUT_PINS.items()),
            'reviewed user-fetch source or retained native recipe differs')
    result['source_sha256'].update(INPUT_PINS)
    if diagnostics:
        require(all(sha(ROOT / name) == digest for name, digest in DIAGNOSTIC_PINS.items()),
                'reviewed compiler diagnostic source differs')
        result['source_sha256'].update(DIAGNOSTIC_PINS)
        result['scope'] = 'public-reference-user-fetch-compiler-diagnostics-no-link-or-runtime'
    if header_context:
        require(diagnostics and sha(ROOT / CONTEXT_HEADER) == CONTEXT_HEADER_SHA256,
                'reviewed BSD header-context regression required')
        result['source_sha256'][CONTEXT_HEADER] = CONTEXT_HEADER_SHA256
        result['scope'] = 'public-reference-user-fetch-bsd-header-context-no-link-or-runtime'
    from test_user_instruction_fetch import REFERENCE_PINS
    from build_native_bootstrap_selection import common_flags, definitions
    from phase1_iostorage_native_complete import (GENERATION_TOOL_SHA256, GENERATION_HEADER_SHA256,
                                                 stage_exports)

    generate(result, output)
    result.update(passed=False, stage='user-fetch-native-context-binding')
    require(result['fresh_tool_sha256'] == GENERATION_TOOL_SHA256 and
            {name: item['sha256'] for name, item in result['fresh_generated_headers'].items()} ==
            GENERATION_HEADER_SHA256, 'accepted native tool/header generation differs')
    work = output / 'native-work'
    context = json.loads((work / 'context.json').read_bytes())
    source = work / 'source'
    compiler = command('xcrun', '-f', 'clang')
    sdk = command('xcrun', '--sdk', 'macosx', '--show-sdk-path')
    require(context['source'] == str(source) and context['compiler'] == compiler and context['sdk'] == sdk and
            context['ci_context']['GITHUB_SHA'] == result['source_head'] and
            context['ci_context']['GITHUB_RUN_ID'] == str(result['run_id']) and
            context['ci_context']['GITHUB_RUN_ATTEMPT'] == '1', 'same-run native context required')
    pins = dict(REFERENCE_PINS, **{'osfmk/arm64/proc_reg.h': NATIVE_PROC_REG_SHA256})
    require(all(sha(source / name) == digest for name, digest in pins.items()),
            'native reference declarations differ from reviewed public source/board patch')
    native = ROOT / 'note10/private/windows-xnu'
    config = native / 'configured/DEVELOPMENT/osfmk'
    configured = json.loads((native / 'configure-result.json').read_bytes())
    rows = [row for row in configured['configured'] if row['variant'] == 'DEVELOPMENT' and
            row['component'] == 'osfmk']
    require(configured['source_directory'] == source.relative_to(ROOT).as_posix() and
            configured['source_commit'] == context['public_source_commit'] and len(rows) == 1 and
            sha(config / 'Makefile') == rows[0]['makefile_sha256'] and
            sha(config / 'meta_features.h') == rows[0]['headers']['meta_features.h'],
            'same-run generated osfmk configuration required')
    defines = definitions((config / 'Makefile').read_text())
    result.update(public_reference_sha256=REFERENCE_PINS, native_reference_sha256=pins,
                  public_xnu_commit=context['public_source_commit'],
                  osfmk_config_defines_sha256=hashlib.sha256(json.dumps(defines, separators=(',', ':')).encode()).hexdigest(),
                  osfmk_config_header_sha256=sha(config / 'meta_features.h'),
                  osfmk_generated_headers_sha256=rows[0]['headers'],
                  osfmk_makefile_sha256=sha(config / 'Makefile'))
    stage_exports(source, native)
    if header_context:
        require(all(sha(source / name) == digest for name, digest in CONTEXT_REFERENCE_PINS.items()) and
                all(sha(native / 'source-exports' / name) == CONTEXT_REFERENCE_PINS[name]
                    for name in ('bsd/sys/types.h', 'bsd/sys/_types/_dev_t.h')),
                'actual public BSD type/string source and exported type headers required')
        result['header_context'] = dict(schema='note10-v164-user-fetch-header-context-v1',
            mach_kernel_private=False, compiled_regression=False,
            regression_header_sha256=CONTEXT_HEADER_SHA256, public_header_sha256=CONTEXT_REFERENCE_PINS)
    obj = output / 'note10_user_instruction_fetch.o'
    # common_flags supplies the accepted generated configuration/SDK include recipe;
    # these C code-generation flags are the retained compile_native_components recipe.
    argv = [compiler, *common_flags(source, config, sdk), '-std=gnu11',
            '-mkernel', '-fno-c++-static-destructors', '-ftrivial-auto-var-init=zero',
            '-fsigned-bitfields', '-fmerge-all-constants', '-fno-strict-aliasing',
            '-momit-leaf-frame-pointer', '-fno-branch-target-identification', '-mno-implicit-sme',
            '-DMACH_KERNEL_PRIVATE', '-DMACH_KERNEL', '-I', str(native / 'exports'),
            '-c', str(ROOT / SOURCE), '-o', str(obj)]
    if header_context:
        # libsa/string.h selects conflicting standalone types only for MACH_KERNEL_PRIVATE.
        require(argv.count('-DMACH_KERNEL_PRIVATE') == 1, 'one inherited Mach-private flag required')
        argv.remove('-DMACH_KERNEL_PRIVATE')
        argv[argv.index('-c'):argv.index('-c')] = ['-include', str(ROOT / CONTEXT_HEADER)]
    (output / 'compiler-argv.internal.json').write_text(json.dumps(argv) + '\n', encoding='utf-8')
    path_options = {'-I', '-include', '-isysroot', '-c', '-o'}
    flags = [arg for index, arg in enumerate(argv[1:], 1)
             if arg not in path_options and argv[index - 1] not in path_options]
    result.update(stage='user-fetch-one-object-compile', compiler_flags=flags,
                  compiler_argv_count=len(argv),
                  compiler_argv_sha256=hashlib.sha256(json.dumps(argv, separators=(',', ':')).encode()).hexdigest(),
                  compile_attempts=1, target_object_compile_attempts=1)
    call = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    result['compiler_returncode'] = call.returncode
    if header_context and call.returncode == 0:
        result['header_context']['compiled_regression'] = True
    if diagnostics:
        from user_instruction_diagnostics import summarize
        result['compiler_diagnostics'] = summarize(call.stderr, {
            str(ROOT / 'note10/xnu26'): 'port', str(source): 'XNU', str(native): 'generated',
            sdk: 'SDK', str(output): 'output', compiler: 'compiler',
        })
    (output / 'compiler.internal.log').write_bytes(call.stdout + call.stderr)
    if call.returncode:
        match = re.search(rb"fatal error: '([A-Za-z0-9_][A-Za-z0-9_./+\-]{0,127})' file not found", call.stderr)
        if match and b'..' not in match.group(1):
            result['missing_include_sha256'] = hashlib.sha256(match.group(1)).hexdigest()
        return
    require_arm64_object(obj)
    result.update(stage='user-fetch-symbol-audit', compiled_arm64_objects=1, object_sha256=sha(obj),
                  object_bytes=obj.stat().st_size)
    nm = ('xcrun', '--sdk', 'macosx', 'nm')
    defined = command(*nm, '-g', '-U', '-j', str(obj)).splitlines()
    undefined = command(*nm, '-u', '-j', str(obj)).splitlines()
    require(len(defined) <= 32 and len(undefined) <= 32 and
            all(re.fullmatch(r'[A-Za-z_.$][A-Za-z0-9_.$]{0,383}', name) for name in defined + undefined),
            'bounded object symbol names required')
    result.update(defined_external_symbols=defined, undefined_external_symbols=undefined)
    require(defined == ['_n10_fetch_user_instruction'] and undefined == ['_copyin'],
            'unexpected user-fetch definitions or imports')
    result.update(stage='complete', passed=True, user_instruction_object_verified=True)
