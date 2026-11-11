"""One changed real USER64 exception caller in the accepted native XNU context."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

from phase1_iostorage_declaration import reviewed_identity
from phase1_iostorage_native_inputs import ROOT, command, generate, require, sha
import prepare_user_exception_fetch as overlay

OUTPUT = ROOT / 'note10/private/v198-user-exception-fetch-once'
SOURCE_FILES = (
    'note10/xnu26/prepare_user_exception_fetch.py', 'note10/xnu26/patches/0015-user-exception-checked-fetch.patch',
    'note10/xnu26/phase1_user_exception_fetch.py', 'note10/xnu26/test_user_exception_fetch.c',
    'note10/xnu26/build_current_native_kernel.py', 'note10/xnu26/current_native_kernel.py',
    'note10/xnu26/phase1_iostorage_kernel_link.py', 'note10/xnu26/phase1_memdev_kernel_integration.py',
    '.github/workflows/note10-phase1-iostorage-declaration-pc.yml',
    'note10/inspect_macho.py',
    *overlay.PINS,
)


def caller_argv(compiler, source, native, sdk, output):
    from build_native_bootstrap_selection import common_flags
    return [compiler, *common_flags(source, native / 'configured/DEVELOPMENT/osfmk', sdk),
            '-std=gnu11', '-mkernel', '-fno-c++-static-destructors', '-ftrivial-auto-var-init=zero',
            '-fsigned-bitfields', '-fmerge-all-constants', '-fno-strict-aliasing', '-momit-leaf-frame-pointer',
            '-fno-branch-target-identification', '-mno-implicit-sme', '-DMACH_KERNEL_PRIVATE', '-DMACH_KERNEL',
            '-I', str(native / 'exports'), '-c', str(source / overlay.REL), '-o', str(output)]


def compile_caller(result, output):
    from phase1_iostorage_native_complete import GENERATION_TOOL_SHA256, GENERATION_HEADER_SHA256, stage_exports
    from user_instruction_diagnostics import summarize
    generate(result, output)
    result.update(passed=False, stage='caller-context-binding')
    require(result['fresh_tool_sha256'] == GENERATION_TOOL_SHA256 and
            {n: v['sha256'] for n, v in result['fresh_generated_headers'].items()} == GENERATION_HEADER_SHA256,
            'accepted fresh native context differs')
    context = json.loads((output / 'native-work/context.json').read_bytes())
    source = Path(context['source'])
    native = ROOT / 'note10/private/windows-xnu'
    compiler = command('xcrun', '-f', 'clang')
    sdk = command('xcrun', '--sdk', 'macosx', '--show-sdk-path')
    ci = context['ci_context']
    require(context['compiler'] == compiler and context['sdk'] == sdk and
            ci['GITHUB_SHA'] == result['source_head'] and ci['GITHUB_RUN_ID'] == str(result['run_id']) and
            ci['GITHUB_RUN_ATTEMPT'] == '1', 'same-run caller context required')
    result['stage'] = 'caller-overlay'
    result['overlay'] = overlay.apply(source, output)
    stage_exports(source, native)
    config = native / 'configured/DEVELOPMENT/osfmk'
    result['native_context'] = dict(makefile_sha256=sha(config / 'Makefile'),
        headers={p.name: sha(p) for p in sorted(config.glob('*.h'))},
        public_source_commit=context['public_source_commit'], saved_state_profile='actual-generated-native-public-reference')
    obj = output / 'user-exception-caller.o'
    argv = caller_argv(compiler, source, native, sdk, obj)
    (output / 'compiler-argv.internal.json').write_text(json.dumps(argv) + '\n')
    result.update(stage='new-caller-compile', target_object_compile_attempts=1)
    call = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=90)
    (output / 'compiler.internal.log').write_bytes(call.stdout + call.stderr)
    result['compiler_returncode'] = call.returncode
    result['compiler_argv_sha256'] = hashlib.sha256(json.dumps(argv, separators=(',', ':')).encode()).hexdigest()
    result['compiler_diagnostics'] = summarize(call.stderr, {str(source): 'XNU', str(native): 'generated',
        str(ROOT / 'note10/xnu26'): 'port', sdk: 'SDK', str(output): 'output', compiler: 'compiler'})
    require(call.returncode == 0, 'one changed caller compile failed; no retry')
    result['stage'] = 'new-caller-symbol-view'
    # A single completed raw read supplies both identity and header checks.
    result['new_object_raw_reads'] += 1
    raw = overlay.read(obj)
    tree = ast.parse(overlay.read(ROOT / 'note10/inspect_macho.py'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'header_commands']
    require(len(nodes) == 1 and not nodes[0].decorator_list, 'unique neutral header reader required')
    scope = {'struct': struct}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'header_commands', 'exec'), scope)
    header, _ = scope['header_commands'](raw)
    require(header[:4] == (0xfeedfacf, 0x100000c, 0, 1), 'matching new caller object required')
    result.update(object_sha256=hashlib.sha256(raw).hexdigest(), object_bytes=len(raw))
    result['new_object_nm_views'] += 1
    view = subprocess.run(['xcrun', '--sdk', 'macosx', 'nm', '-m', str(obj)], cwd=ROOT,
                          capture_output=True, timeout=30)
    (output / 'nm.internal.log').write_bytes(view.stdout + view.stderr)
    require(view.returncode == 0 and len(view.stdout) <= 131072, 'bounded new caller symbol view required')
    defined, undefined = [], []
    for line in view.stdout.decode('utf-8').splitlines():
        if 'non-external' in line or not re.search(r'\bexternal\b', line):
            continue
        name = line.split()[-1]
        require(re.fullmatch(r'_[A-Za-z0-9_.$]{1,383}', name), 'bounded external symbol name required')
        (undefined if '(undefined)' in line else defined).append(name)
    require(len(defined) <= 256 and len(undefined) <= 256 and
            len(set(defined)) == len(defined) and len(set(undefined)) == len(undefined) and
            undefined.count('_n10_fetch_user_instruction') == 1 and '_n10_fetch_user_instruction' not in defined,
            'new actual caller must import the genuine fetch')
    result.update(stage='complete', passed=True, caller_compile_verified=True,
                  defined_external_symbols=sorted(defined), undefined_external_symbols=sorted(undefined))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    head, run = reviewed_identity()
    require(os.environ.get('N10_PROBE_MODE') == 'user_exception_fetch' and
            (ROOT / args.output).resolve() == OUTPUT and not OUTPUT.exists(), 'exact new mode and fresh output required')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    result = dict(schema='note10-v198-user-exception-fetch-native-result-v1', source_head=head, run_id=run,
                  run_attempt=1, target='arm64-apple-ios26.5.2', scope='real-USER64-caller-source-compile-no-runtime',
                  stage='source-binding', passed=False, caller_compile_verified=False,
                  source_sha256={n: sha(ROOT / n) for n in SOURCE_FILES}, target_object_compile_attempts=0,
                  new_object_raw_reads=0, new_object_nm_views=0, unchanged_fetch_compiles=0,
                  kernel_builds=0, kernel_links=0, old_tests_count=0, device_operations=0,
                  firmware_abi_verified=False, runtime_copyin_verified=False, runtime_task_map_observed=False,
                  user_mapping_installed=False, native_activation=False, physical_ready=False)
    try:
        compile_caller(result, OUTPUT)
    except Exception as error:
        result.update(passed=False, failure_type=type(error).__name__)
    # Native generation exposes private paths in intermediate metadata; publish only these fields.
    fields = '''schema source_head run_id run_attempt target scope stage passed failure_type source_sha256
        caller_compile_verified target_object_compile_attempts compiler_returncode compiler_argv_sha256
        compiler_diagnostics native_context overlay fresh_tool_sha256 compiler_version sdk_version
        native_inputs_generated host_config_tool_built new_object_raw_reads new_object_nm_views object_sha256
        object_bytes defined_external_symbols undefined_external_symbols unchanged_fetch_compiles kernel_builds
        kernel_links old_tests_count device_operations firmware_abi_verified runtime_copyin_verified
        runtime_task_map_observed user_mapping_installed native_activation physical_ready'''.split()
    public = {k: result[k] for k in fields if k in result}
    (OUTPUT / 'result.json').write_text(json.dumps(public, sort_keys=True, indent=2) + '\n')
    return 0 if public['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
