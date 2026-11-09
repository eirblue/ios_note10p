"""One reviewed PC-only final link with six fresh storage objects."""
import json
from pathlib import Path
import re

import build_current_native_kernel as builder
import current_native_kernel as native
import phase1_iostorage_declaration as sdk
import phase1_iostorage_native_complete as complete
from phase1_iostorage_native_inputs import (
    FIREHOSE_SHA256, KDK_SHA256, ROOT, XNU_COMMIT, command, fresh_headers, require, sha, verify_retained_inputs,
)


PRIVATE = ROOT / 'note10/private'
WORK = PRIVATE / 'phase1-iostorage-declaration-once/native-work'
OUTPUT = PRIVATE / 'phase1-iostorage-final-link-once'
SUMMARY = PRIVATE / 'phase1-iostorage-final-link-result/result.json'


def verify_sources():
    verify_retained_inputs()
    pins = sdk.CLOSURE_INPUT_SHA256 | {sdk.NATIVE_INPUTS_SOURCE: sdk.NATIVE_INPUTS_SHA256}
    require(all(sha(ROOT / path) == digest for path, digest in pins.items()), 'storage source pins differ')


def storage_units(directory):
    apple = directory / 'apple-implementation'
    public = directory / 'public-sdk-objects'
    units = [
        (apple / complete.MEMBER, apple, complete.MEMBER_SHA256),
        (public / sdk.BASE_MEMBER, public, sdk.BASE_MEMBER_SHA),
    ]
    units.extend((ROOT / source, public, sdk.CLOSURE_INPUT_SHA256[source])
                 for source in (sdk.PROVIDER_SOURCE, sdk.PIO_SOURCE, *sdk.PIO_LINK_C_SOURCES))
    return [(source, owner / (source.stem + '.o'), digest) for source, owner, digest in units]


def compile_storage(current, work, output, result):
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
    objects = sdk.compile_closure_objects(result, directory, native_work=work)
    units = storage_units(directory)
    require(objects == [str(obj) for _, obj, _ in units] and result['compile_attempts'] == 6 and
            result['archive_fetch_attempts'] == 1 and result['fresh_inputs_reverified'],
            'six exact same-run storage objects required')

    proof = dict(producer_id=current['producer_id'], input_binding=current['input_binding'],
                 compiler=toolchain['compiler'], sdk=toolchain['sdk'], archive_sha256=sdk.ARCHIVE_SHA,
                 public_sdk_header_sha256=result['sdk_header_sha256'],
                 generated_headers=result['fresh_generated_headers'], tools=result['fresh_tool_sha256'])
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
    require(current['producer']['ci_context'] == builder.ci_context(checked=True, storage=True),
            'dedicated same-run storage producer required')
    directory = output / 'storage'
    units = storage_units(directory)
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
    require(len(native_paths) == 1071 and len(rows) == len(units) == 6, 'exact final object counts required')
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


def verify_final_symbols(symbols, linked, result):
    required, vtable = sdk.closure_symbols()
    defined = [parts[-1] for line in symbols.splitlines() if len(parts := line.split()) >= 3 and
               re.fullmatch(r'[0-9a-fA-F]+', parts[0]) and parts[-2].isupper()]
    require(linked['object_count'] == 1077 and all(defined.count(name) == 1 for name in (*required, vtable)),
            'final storage definitions or object count differ')
    result.update(stage='storage-linked', final_storage_symbols_verified=True)


def main():
    ci = builder.ci_context(checked=True, storage=True)
    SUMMARY.parent.mkdir(parents=True)
    result = dict(schema='note10-phase1-iostorage-final-link-result-v1', passed=False,
                  source_head=ci['GITHUB_SHA'], run_id=int(ci['GITHUB_RUN_ID']), run_attempt=1,
                  old_suites_executed=0, device_operations=0, deployment_ready=False,
                  source_sha256={name: sha(ROOT / name) for name in (
                      builder.STORAGE_WORKFLOW, 'note10/xnu26/build_current_native_kernel.py',
                      'note10/xnu26/current_native_kernel.py', 'note10/xnu26/phase1_iostorage_kernel_link.py',
                      'note10/xnu26/phase1_iostorage_declaration.py', sdk.NATIVE_COMPLETE_SOURCE,
                      sdk.NATIVE_INPUTS_SOURCE, *[name for name in sdk.CLOSURE_INPUT_SHA256
                                                  if name != sdk.NATIVE_COMPLETE_SOURCE])})
    try:
        builder.build(builder.bootstrap.private(WORK), builder.bootstrap.private(OUTPUT), storage=True)
    except Exception as error:
        result['failure_type'] = type(error).__name__
    path = OUTPUT / 'result.json'
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
    SUMMARY.write_bytes((json.dumps(result, sort_keys=True, indent=2) + '\n').encode())
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
