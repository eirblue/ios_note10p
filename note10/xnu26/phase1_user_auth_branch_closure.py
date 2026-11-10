"""One native three-input relocatable closure; no standalone unit gates or runtime."""
import hashlib
import json
import re
import subprocess

from phase1_iostorage_native_inputs import ROOT, command, generate, require, sha

RETAINED_BUILDER = 'note10/xnu26/phase1_user_instruction_fetch.py'
RETAINED_BUILDER_SHA256 = '74aec7aedd981d4831d14da28a1b26d80f5eb8505c54cd9f9cbc89a66f0bfcb7'
DECODER_MARKER = b'\nenum n10_step_result n10_step_auth_branch('
DECODER_BYTES = 1523
DECODER_SHA256 = '17b34248d595c4a9ea4542feb1f28f8633cd708571d03a7ee67b9ed6a4611133'
DEFINITIONS = ['_n10_decode_auth_branch', '_n10_decode_user_auth_branch', '_n10_fetch_user_instruction']
IMPORTS = ['_bzero', '_copyin', '_memcpy']
CARRIED = {
    'host4_result_sha256': '41ef842d814efa3cf2847c00f067b0857cb5ca53d6dfdfd82eed988c7b2437de',
    'fetch_native_result_sha256': '92b62b546b0f4c9efde26ee3090e89c50b40b7344828ae2f19c2b33b58f6d492',
    'wrapper_original_result_sha256': '94c4f75c93df27903c7d9e6af105c465f1fcb4392fd72d8ba1b5aedd8eaab4f3',
    'wrapper_original_CI_passed': False,
    'wrapper_local_import_summary_sha256': 'abece52fe3e4bfbd930b477cdb75eb85a75b68015eb334d3d4a38762ad778e66',
    'wrapper_local_import_accepted': True,
}


def link_diagnostics(raw, roots, summarize):
    # Apple ld omits a severity on some errors; retain its message using the existing safe parser.
    text = re.sub(rb'(?m)^ld: (?!(?:fatal error|error|warning|note): )', b'error: ', raw[:65536])
    text = re.sub(rb'(?m)^ld: ', b'', text)
    observed = summarize(text, roots)
    observed.update(stderr_sha256=hashlib.sha256(raw).hexdigest(), stderr_bytes=len(raw),
                    input_truncated=len(raw) > 65536)
    return observed


def compile_auth_branch_closure(result, output, require_arm64_object):
    result.update(passed=False, scope='public-reference-user-fetch-auth-branch-link-closure-no-runtime',
                  stage='closure-source-binding', closure_verified=False, compile_attempts=0,
                  target_object_compile_attempts=0, compiled_arm64_objects=0, partial_link_attempts=0,
                  kernel_links=0, production_hook=False, firmware_abi_verified=False,
                  synthetic_board_inputs=True, exact_target_source=False, units=[])
    require(sha(ROOT / RETAINED_BUILDER) == RETAINED_BUILDER_SHA256, 'accepted native context recipe differs')
    from phase1_user_instruction_fetch import (INPUT_PINS, DIAGNOSTIC_PINS, AUTH_BRANCH_PINS,
        CONTEXT_HEADER, CONTEXT_HEADER_SHA256, CONTEXT_REFERENCE_PINS, NATIVE_PROC_REG_SHA256)
    pins = {RETAINED_BUILDER: RETAINED_BUILDER_SHA256, **INPUT_PINS, **DIAGNOSTIC_PINS,
            **AUTH_BRANCH_PINS, CONTEXT_HEADER: CONTEXT_HEADER_SHA256}
    require(all(sha(ROOT / name) == digest for name, digest in pins.items()), 'exact closure source inputs differ')
    result['source_sha256'].update(pins)
    result['carried_evidence'] = CARRIED
    from test_user_instruction_fetch import REFERENCE_PINS
    from build_native_bootstrap_selection import common_flags, definitions
    from phase1_iostorage_native_complete import GENERATION_TOOL_SHA256, GENERATION_HEADER_SHA256, stage_exports
    from user_instruction_diagnostics import summarize

    generate(result, output)
    result.update(passed=False, stage='closure-native-context-binding')
    result['generated_header_sha256'] = sorted(row['sha256'] for row in result['fresh_generated_headers'].values())
    require(result['fresh_tool_sha256'] == GENERATION_TOOL_SHA256 and
            {name: row['sha256'] for name, row in result['fresh_generated_headers'].items()} == GENERATION_HEADER_SHA256,
            'accepted native generation tools/headers differ')
    work = output / 'native-work'
    context = json.loads((work / 'context.json').read_bytes())
    source = work / 'source'
    compiler = command('xcrun', '-f', 'clang')
    sdk = command('xcrun', '--sdk', 'macosx', '--show-sdk-path')
    require(context['source'] == str(source) and context['compiler'] == compiler and context['sdk'] == sdk and
            context['ci_context']['GITHUB_SHA'] == result['source_head'] and
            context['ci_context']['GITHUB_RUN_ID'] == str(result['run_id']) and
            context['ci_context']['GITHUB_RUN_ATTEMPT'] == '1', 'same-run generated native context required')
    native_pins = dict(REFERENCE_PINS, **{'osfmk/arm64/proc_reg.h': NATIVE_PROC_REG_SHA256})
    require(all(sha(source / name) == digest for name, digest in native_pins.items()), 'native declarations differ')
    native = ROOT / 'note10/private/windows-xnu'
    config = native / 'configured/DEVELOPMENT/osfmk'
    configured = json.loads((native / 'configure-result.json').read_bytes())
    rows = [row for row in configured['configured'] if row['variant'] == 'DEVELOPMENT' and row['component'] == 'osfmk']
    require(configured['source_directory'] == source.relative_to(ROOT).as_posix() and
            configured['source_commit'] == context['public_source_commit'] and len(rows) == 1 and
            sha(config / 'Makefile') == rows[0]['makefile_sha256'] and
            sha(config / 'meta_features.h') == rows[0]['headers']['meta_features.h'], 'fresh osfmk configuration required')
    flags = definitions((config / 'Makefile').read_text())
    result.update(public_reference_sha256=REFERENCE_PINS, native_reference_sha256=native_pins,
                  public_xnu_commit=context['public_source_commit'],
                  osfmk_config_defines_sha256=hashlib.sha256(json.dumps(flags, separators=(',', ':')).encode()).hexdigest(),
                  osfmk_config_header_sha256=sha(config / 'meta_features.h'),
                  osfmk_generated_headers_sha256=rows[0]['headers'], osfmk_makefile_sha256=sha(config / 'Makefile'))
    stage_exports(source, native)
    require(all(sha(source / name) == digest for name, digest in CONTEXT_REFERENCE_PINS.items()) and
            all(sha(native / 'source-exports' / name) == CONTEXT_REFERENCE_PINS[name]
                for name in ('bsd/sys/types.h', 'bsd/sys/_types/_dev_t.h')), 'actual BSD type/string sources required')
    result['header_context'] = dict(schema='note10-v164-user-fetch-header-context-v1',
        mach_kernel_private=False, compiled_regression=False,
        regression_header_sha256=CONTEXT_HEADER_SHA256, public_header_sha256=CONTEXT_REFERENCE_PINS)

    result['stage'] = 'closure-decoder-source-binding'
    original = ROOT / 'note10/compat/auth_branch.c'
    raw = original.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == AUTH_BRANCH_PINS['note10/compat/auth_branch.c'] and
            raw.count(DECODER_MARKER) == 1, 'exact whole source and unique complete decoder boundary required')
    prefix = raw.split(DECODER_MARKER, 1)[0]
    require(len(prefix) == DECODER_BYTES and hashlib.sha256(prefix).hexdigest() == DECODER_SHA256,
            'exact original decoder function prefix required')
    decoder = output / 'decoder-only.c'
    with decoder.open('xb') as stream:
        stream.write(prefix)
    result['decoder_source'] = dict(original_source='note10/compat/auth_branch.c',
        original_sha256=AUTH_BRANCH_PINS['note10/compat/auth_branch.c'], prefix_bytes=DECODER_BYTES,
        prefix_sha256=DECODER_SHA256, complete_function=True, body_modified=False)
    base = [compiler, *common_flags(source, config, sdk), '-std=gnu11', '-mkernel',
            '-fno-c++-static-destructors', '-ftrivial-auto-var-init=zero', '-fsigned-bitfields',
            '-fmerge-all-constants', '-fno-strict-aliasing', '-momit-leaf-frame-pointer',
            '-fno-branch-target-identification', '-mno-implicit-sme', '-DMACH_KERNEL',
            '-I', str(native / 'exports'), '-include', str(ROOT / CONTEXT_HEADER)]
    require(not any(arg == '-DMACH_KERNEL_PRIVATE' or arg.startswith('-DMACH_KERNEL_PRIVATE=') for arg in base),
            'BSD-aware type context required')
    roots = {str(ROOT / 'note10/xnu26'): 'port', str(ROOT / 'note10/compat'): 'compat',
             str(source): 'XNU', str(native): 'generated', sdk: 'SDK', str(output): 'output', compiler: 'compiler'}
    inputs = (('fetch', ROOT / 'note10/xnu26/note10_user_instruction_fetch.c', INPUT_PINS['note10/xnu26/note10_user_instruction_fetch.c']),
              ('wrapper', ROOT / 'note10/xnu26/note10_user_auth_branch.c', AUTH_BRANCH_PINS['note10/xnu26/note10_user_auth_branch.c']),
              ('decoder', decoder, DECODER_SHA256))
    objects = []
    for name, input_source, digest in inputs:
        result['stage'] = 'closure-' + name + '-source-binding'
        require(sha(input_source) == digest, 'direct closure source changed before compile')
        obj = output / (name + '.o')
        argv = [*base]
        if name == 'decoder':
            argv[1:1] = ['-I', str(ROOT / 'note10/compat')]
        argv += ['-c', str(input_source), '-o', str(obj)]
        with (output / (name + '-argv.internal.json')).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(argv) + '\n')
        path_options = {'-I', '-include', '-isysroot', '-c', '-o'}
        safe_flags = [arg for i, arg in enumerate(argv[1:], 1) if arg not in path_options and argv[i-1] not in path_options]
        row = dict(name=name, source_sha256=digest, compiler_argv_count=len(argv),
                   compiler_argv_sha256=hashlib.sha256(json.dumps(argv, separators=(',', ':')).encode()).hexdigest(),
                   compiler_flags=safe_flags)
        result['units'].append(row)
        result['compile_attempts'] += 1
        result['target_object_compile_attempts'] += 1
        result['stage'] = 'closure-' + name + '-compile'
        try:
            call = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
        except subprocess.TimeoutExpired as error:
            row.update(timed_out=True, compiler_diagnostics=summarize(error.stderr or b'', roots))
            (output / (name + '.internal.log')).write_bytes((error.stdout or b'') + (error.stderr or b''))
            raise
        row.update(compiler_returncode=call.returncode, compiler_diagnostics=summarize(call.stderr, roots))
        (output / (name + '.internal.log')).write_bytes(call.stdout + call.stderr)
        if call.returncode:
            return
        if len(result['units']) == 3:
            result['header_context']['compiled_regression'] = True
        require_arm64_object(obj)
        row.update(object_sha256=sha(obj), object_bytes=obj.stat().st_size, ARM64_object=True)
        result['compiled_arm64_objects'] += 1
        objects.append(str(obj))

    result.update(stage='closure-relocatable-link', partial_link_attempts=1)
    merged = output / 'note10_user_auth_branch_closure.o'
    argv = ['xcrun', '--sdk', 'macosx', 'ld', '-r', '-arch', 'arm64', '-o', str(merged), *objects]
    with (output / 'link-argv.internal.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(argv) + '\n')
    result['link'] = dict(argv_count=len(argv), argv_sha256=hashlib.sha256(json.dumps(argv, separators=(',', ':')).encode()).hexdigest(),
                          diagnostic_format='apple-ld-prefix-to-safe-summary-v1')
    try:
        call = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired as error:
        result['link'].update(timed_out=True, diagnostics=link_diagnostics(error.stderr or b'', roots, summarize))
        (output / 'link.internal.log').write_bytes((error.stdout or b'') + (error.stderr or b''))
        raise
    result['partial_link_returncode'] = call.returncode
    result['link'].update(returncode=call.returncode, diagnostics=link_diagnostics(call.stderr, roots, summarize))
    (output / 'link.internal.log').write_bytes(call.stdout + call.stderr)
    if call.returncode:
        return
    require_arm64_object(merged)
    result.update(stage='closure-symbol-audit', merged_object_sha256=sha(merged), merged_object_bytes=merged.stat().st_size)
    nm = ('xcrun', '--sdk', 'macosx', 'nm')
    defined = command(*nm, '-g', '-U', '-j', str(merged)).splitlines()
    undefined = command(*nm, '-u', '-j', str(merged)).splitlines()
    require(len(defined) <= 32 and len(undefined) <= 32 and
            all(re.fullmatch(r'[A-Za-z_.$][A-Za-z0-9_.$]{0,383}', name) for name in defined + undefined),
            'bounded closure symbol names required')
    result.update(defined_external_symbols=defined, undefined_external_symbols=undefined)
    require(sorted(defined) == DEFINITIONS and sorted(undefined) == IMPORTS, 'exact three-definition/kernel-import closure required')
    result.update(stage='complete', passed=True, closure_verified=True)
