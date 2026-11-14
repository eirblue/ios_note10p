"""One reviewed PC-only final link with six fresh storage objects."""
import argparse
import json
import os
from pathlib import Path
import re

import build_current_native_kernel as builder
import current_native_kernel as native
import phase1_iostorage_declaration as sdk
import phase1_iostorage_native_complete as complete
import phase1_readonly_ram_block_device as ram
from phase1_iostorage_native_inputs import (
    FIREHOSE_SHA256, KDK_SHA256, ROOT, XNU_COMMIT, command, fresh_headers, require, sha, verify_retained_inputs,
)


PRIVATE = ROOT / 'note10/private'
WORK = PRIVATE / 'phase1-iostorage-declaration-once/native-work'
OUTPUT = PRIVATE / 'phase1-iostorage-final-link-once'
SUMMARY = PRIVATE / 'phase1-iostorage-final-link-result/result.json'


def verify_sources(readonly_ram_nub=False):
    verify_retained_inputs()
    pins = ram.selected_sources(readonly_ram_nub) | {sdk.NATIVE_INPUTS_SOURCE: sdk.NATIVE_INPUTS_SHA256}
    require(all(sha(ROOT / path) == digest for path, digest in pins.items()), 'storage source pins differ')


def storage_units(directory, readonly_ram_nub=False):
    pins = ram.selected_sources(readonly_ram_nub)
    apple = directory / 'apple-implementation'
    public = directory / 'public-sdk-objects'
    units = [
        (apple / complete.MEMBER, apple, complete.MEMBER_SHA256),
        (public / sdk.BASE_MEMBER, public, sdk.BASE_MEMBER_SHA),
    ]
    units.extend((ROOT / source, public, pins[source])
                 for source in (ram.NUB_SOURCE if readonly_ram_nub else sdk.PROVIDER_SOURCE, sdk.PIO_SOURCE, *sdk.PIO_LINK_C_SOURCES))
    return [(source, owner / (source.stem + '.o'), digest) for source, owner, digest in units]


def compile_storage(current, work, output, result, *, diagnostic_sink=None):
    directory = output / 'storage'
    directory.mkdir()
    ci = current['producer']['ci_context']
    toolchain = current['producer']['toolchain']
    require(current['producer']['public_source_commit'] == XNU_COMMIT and
            current['bindings']['public_firehose_header_sha256'] == FIREHOSE_SHA256 and
            current['bindings']['KDK_public_input_sha256'] == KDK_SHA256,
            'accepted native source and declaration pins required')
    require(command('xcrun', '-f', 'clang') == toolchain['compiler'] and
            command('xcrun', '--sdk', 'macosx', '--show-sdk-path') == toolchain['sdk'],
            'storage and native compiler/SDK differ')
    result.update(stage='storage-input-binding', source_head=ci['GITHUB_SHA'], run_id=int(ci['GITHUB_RUN_ID']),
                  native_complete_verified=False, compile_attempts=0, target_object_compile_attempts=0,
                  compiled_arm64_objects=0, archive_fetch_attempts=0,
                  fresh_generated_headers=fresh_headers(PRIVATE / 'windows-xnu'),
                  fresh_tool_sha256={name: sha(Path(command('xcrun', '-f', name)))
                                     for name in complete.GENERATION_TOOL_SHA256})
    selected = ram.enabled(current)
    objects = sdk.compile_closure_objects(result, directory, native_work=work, diagnostic_sink=diagnostic_sink,
                                          readonly_ram_nub=selected)
    units = storage_units(directory, selected)
    require(objects == [str(obj) for _, obj, _ in units] and result['compile_attempts'] == 6 and
            result['archive_fetch_attempts'] == 1 and result['fresh_inputs_reverified'],
            'six exact same-run storage objects required')

    proof = dict(producer_id=current['producer_id'], input_binding=current['input_binding'],
                 compiler=toolchain['compiler'], sdk=toolchain['sdk'], archive_sha256=sdk.ARCHIVE_SHA,
                 public_sdk_header_sha256=result['sdk_header_sha256'],
                 generated_headers=result['fresh_generated_headers'], tools=result['fresh_tool_sha256'])
    if selected:
        proof.update(readonly_ram_nub=ram.profile(), readonly_ram_sdk_delta_sha256=result['readonly_ram_sdk_delta_sha256'])
    binding = native.digest(proof)
    current['storage'] = {'proof': proof, 'binding': binding}
    rows = []
    for source, obj, digest in units:
        require(sha(source) == digest, 'compiled storage source pin differs')
        row = dict(source='@storage/' + source.name, source_sha256=digest, passed=True, object_path=str(obj),
                   object_sha256=sha(obj), storage_binding=binding)
        native.stamp(current, row, 'storage')
        rows.append(row)
    builder.bootstrap.write_json(output / 'storage-receipts.json', {'binding': current['storage'], 'units': rows})
    result.update(stage='storage-objects-ready', storage_binding_sha256=binding,
                  storage_object_sha256={row['source']: row['object_sha256'] for row in rows})
    return rows


def admit_storage(current, rows, output, native_paths):
    require(current['producer']['ci_context'] == builder.ci_context(checked=True, storage=True, owned_ram_factory=__import__('phase1_owned_ram_kernel_integration').enabled(current)),
            'dedicated same-run storage producer required')
    directory = output / 'storage'
    selected = ram.enabled(current)
    units = storage_units(directory, selected)
    storage = current['storage']
    proof = storage['proof']
    toolchain = current['producer']['toolchain']
    require(storage['binding'] == native.digest(proof) and proof['producer_id'] == current['producer_id'] and
            proof['input_binding'] == current['input_binding'] and proof['compiler'] == toolchain['compiler'] and
            proof['sdk'] == toolchain['sdk'] and proof['archive_sha256'] == sdk.ARCHIVE_SHA and
            proof['tools'] == complete.GENERATION_TOOL_SHA256 and
            {name: item['sha256'] for name, item in proof['generated_headers'].items()} ==
            complete.GENERATION_HEADER_SHA256 and
            native.digest(proof['public_sdk_header_sha256']) == sdk.CLOSURE_PUBLIC_SDK_SHA256,
            'storage input binding differs')
    require((proof.get('readonly_ram_nub') == ram.profile() and
             proof.get('readonly_ram_sdk_delta_sha256') == ram.SDK_DELTA) if selected else
            not ({'readonly_ram_nub', 'readonly_ram_sdk_delta_sha256'} & set(proof)), 'closed storage profile required')
    require(len(native_paths) == native.expected_objects(current) and len(rows) == len(units) == 6,
            'exact final object counts required')
    admitted = []
    for row, (source, obj, digest) in zip(rows, units):
        path = native.owned(row['object_path'], directory)
        require(row['source'] == '@storage/' + source.name and row['source_sha256'] == digest and
                row['category'] == 'storage' and row['passed'] is True and
                row['producer_id'] == current['producer_id'] and row['input_binding'] == current['input_binding'] and
                row['storage_binding'] == storage['binding'] and path == obj and
                sha(path) == row['object_sha256'] and sha(source) == digest,
                'storage object ownership or source binding differs')
        sdk.require_arm64_object(path)
        admitted.append(path)
    require(len(set(admitted)) == 6 and not (set(admitted) & set(native_paths)), 'storage object path collision')
    return admitted


def verify_final_symbols(symbols, linked, result, *, current=None):
    required, vtable = sdk.closure_symbols()
    if current is not None and ram.enabled(current):
        vtable = ram.NUB_VTABLE
    defined = [parts[-1] for line in symbols.splitlines() if len(parts := line.split()) >= 3 and
               re.fullmatch(r'[0-9a-fA-F]+', parts[0]) and parts[-2].isupper()]
    count = native.expected_objects(current, storage=True) if current is not None else 1077
    require(linked['object_count'] == count and all(defined.count(name) == 1 for name in (*required, vtable)),
            'final storage definitions or object count differ')
    result.update(stage='storage-linked', final_storage_symbols_verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--memdev-wide-extent', action='store_true')
    modes.add_argument('--memdev-handoff-artifact', action='store_true')
    modes.add_argument('--memdev-compact-artifact', action='store_true')
    parser.add_argument('--user-exception-fetch', action='store_true',
                        help='opt-in checked USER64 caller and genuine fetch provider for normal builds')
    parser.add_argument('--readonly-ram-nub', action='store_true', help='replace the probe storage unit with the real read-only RAM nub')
    args = parser.parse_args()
    compact = args.memdev_compact_artifact
    artifact = args.memdev_handoff_artifact or compact
    fetch_artifact = args.user_exception_fetch and compact
    nub_artifact = args.readonly_ram_nub and artifact
    if nub_artifact and not fetch_artifact:
        parser.error('the new nub artifact requires compact user-exception-fetch mode')
    if fetch_artifact:
        require(os.environ.get('N10_LINK_MODE') == ('readonly_ram_nub_compact_artifact' if nub_artifact else
                'user_exception_fetch_compact_artifact'), 'exact new artifact mode required')
    if args.user_exception_fetch and artifact and not compact:
        parser.error('the frozen v173/v174 artifact routes do not accept the new caller/provider profile')
    memdev = args.memdev_wide_extent or artifact
    work = PRIVATE / 'v170-memdev-kernel-link-work' if memdev else WORK
    output = PRIVATE / 'v170-memdev-kernel-link-once' if memdev else OUTPUT
    summary = PRIVATE / 'v170-memdev-kernel-link-result/result.json' if memdev else SUMMARY
    if artifact:
        work = PRIVATE / 'v173-native-kernel-artifact-work'
        output = PRIVATE / 'v173-native-kernel-artifact-build'
        summary = PRIVATE / 'v173-native-kernel-artifact-result/result.json'
    if compact:
        work = PRIVATE / 'v174-native-kernel-artifact-work'
        output = PRIVATE / 'v174-native-kernel-artifact-build'
        summary = PRIVATE / 'v174-native-kernel-artifact-result/result.json'
    if fetch_artifact:
        work = PRIVATE / 'v200-native-kernel-artifact-work'
        output = PRIVATE / 'v200-native-kernel-artifact-build'
        summary = PRIVATE / 'v200-native-kernel-artifact-result/result.json'
    if nub_artifact:
        work = PRIVATE / 'v204-native-kernel-artifact-work'
        output = PRIVATE / 'v204-native-kernel-artifact-build'
        summary = PRIVATE / 'v204-native-kernel-artifact-result/result.json'
    ci = builder.ci_context(checked=True, storage=True)
    summary.parent.mkdir(parents=True)
    result = dict(schema='note10-phase1-iostorage-final-link-result-v1', passed=False,
                  source_head=ci['GITHUB_SHA'], run_id=int(ci['GITHUB_RUN_ID']), run_attempt=1,
                  old_suites_executed=0, device_operations=0, deployment_ready=False,
                  source_sha256={name: sha(ROOT / name) for name in (
                      builder.STORAGE_WORKFLOW, 'note10/xnu26/build_current_native_kernel.py',
                      'note10/xnu26/current_native_kernel.py', 'note10/xnu26/phase1_iostorage_kernel_link.py',
                      'note10/xnu26/phase1_iostorage_declaration.py', sdk.NATIVE_COMPLETE_SOURCE,
                      sdk.NATIVE_INPUTS_SOURCE, *[name for name in ram.selected_sources(args.readonly_ram_nub)
                                                  if name != sdk.NATIVE_COMPLETE_SOURCE])})
    if memdev:
        result.update(schema='note10-v170-memdev-kernel-link-result-v1',
            scope='public-reference-patched-memdev1078-kernel-link-no-runtime' if args.user_exception_fetch else
                  'public-reference-patched-memdev1077-kernel-link-no-runtime',
            physical_ready=False, runtime_executed=False, firmware_abi_verified=False)
        result['source_sha256'].update({name: sha(ROOT / name) for name in (
            'note10/xnu26/phase1_memdev_kernel_integration.py', 'note10/xnu26/prepare_memdev_wide_extent.py',
            'note10/xnu26/patches/0014-memdev-wide-byte-extent.patch', 'note10/xnu26/user_instruction_diagnostics.py')})
    if artifact:
        result.update(schema='note10-v173-native-kernel-artifact-result-v1',
                      scope='public-reference-patched-kernel-retention-PC-handoff-no-runtime')
        result['source_sha256'].update({name: sha(ROOT / name) for name in (
            'note10/xnu26/native_handoff_artifact.py', 'note10/device_test/bundle_affinity_evidence.py',
            'note10/device_test/sealed_affinity_artifact.cjs')})
    if compact:
        result.update(schema='note10-v174-native-kernel-artifact-result-v1',
                      scope='public-reference-patched-kernel-compact-retention-PC-handoff-no-runtime')
        result['source_sha256']['note10/xnu26/compact_native_receipts.py'] = sha(ROOT/'note10/xnu26/compact_native_receipts.py')
    if fetch_artifact:
        result.update(schema='note10-v200-user-exception-kernel-artifact-result-v1',
                      scope='public-reference-real-user-exception-1078-link-provenance-no-runtime')
        result['source_sha256'].update({name: sha(ROOT / name) for name in (
            'note10/xnu26/prepare_user_exception_fetch.py', 'note10/xnu26/note10_user_instruction_fetch.c',
            'note10/xnu26/note10_user_instruction_fetch.h', 'note10/xnu26/user_instruction_header_context.h',
            'note10/xnu26/patches/0015-user-exception-checked-fetch.patch',
            'note10/xnu26/test_readonly_ram_kernel_profile.py' if args.readonly_ram_nub else
            'note10/xnu26/test_user_exception_kernel_artifact.py')})
    if args.readonly_ram_nub:
        result['source_sha256'].update({name: sha(ROOT / name) for name in (
            'note10/xnu26/phase1_readonly_ram_block_device.py', 'note10/xnu26/test_readonly_ram_kernel_profile.py')})
    if nub_artifact:
        result.update(schema='note10-v204-readonly-ram-nub-kernel-artifact-result-v1',
                      scope='public-reference-real-readonly-ram-nub-1078-static-link-no-runtime')
    try:
        builder.build(builder.bootstrap.private(work), builder.bootstrap.private(output), storage=True, memdev=memdev,
                      user_exception_fetch=args.user_exception_fetch, readonly_ram_nub=args.readonly_ram_nub)
    except BaseException as error:
        if not memdev and not isinstance(error, Exception):
            raise
        result['failure_type'] = type(error).__name__
    path = output / 'result.json'
    state = json.loads(path.read_bytes()) if path.is_file() else {}
    link = state.get('link', {})
    storage = state.get('storage', {})
    attempts = int(link['attempted']) if 'attempted' in link else (
        None if storage.get('stage') == 'storage-final-link' else 0)
    result.update(native_stage=state.get('phase', 'preflight'), storage_stage=storage.get('stage', 'pending'),
                  storage_compiles=storage.get('target_object_compile_attempts', 0),
                  storage_objects=storage.get('compiled_arm64_objects', 0),
                  archive_fetch_attempts=storage.get('archive_fetch_attempts', 0),
                  storage_binding_sha256=storage.get('storage_binding_sha256'),
                  storage_object_sha256=storage.get('storage_object_sha256', {}),
                  storage_compile_returncodes=storage.get('unit_compiler_returncodes', {}),
                  final_link_attempts=attempts, final_link_returncode=link.get('returncode'),
                  final_object_count=link.get('object_count', 0), native_objects=state.get('native_objects', 0),
                  dependency_objects=state.get('dependency_objects', 0),
                  final_storage_symbols_verified=storage.get('final_storage_symbols_verified', False),
                  passed=state.get('passed') is True and storage.get('final_storage_symbols_verified') is True)
    if result['passed']:
        result.update(kernel_sha256=state['output_sha256'], kernel_bytes=state['output_bytes'],
                      undefined_external_count=0)
    if memdev:
        result['memdev_integration'] = state.get('memdev', dict(stage='provisioning',
            failure_code='provisioning_failed', patch_apply_attempts=0, final_link_attempts=0,
            total_target_compile_attempts=0, kernel_link_verified=False))
        result['passed'] = result['passed'] and result['memdev_integration']['kernel_link_verified'] is True
    if fetch_artifact:
        result['user_exception_fetch_link'] = state.get('user_exception_fetch_link', {})
        result['user_exception_tool_counts'] = state.get('user_exception_tool_counts', {})
        result['passed'] = (result['passed'] and result['user_exception_fetch_link'].get('passed') is True and
                            result['user_exception_tool_counts'].get('counts_complete') is True and
                            result['final_object_count'] == 1078)
    if args.readonly_ram_nub:
        result['readonly_ram_nub'] = state.get('readonly_ram_nub', ram.begin())
        result['passed'] = result['passed'] and result['readonly_ram_nub']['passed'] is True
    summary.write_bytes((json.dumps(result, sort_keys=True, indent=2) + '\n').encode())
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
