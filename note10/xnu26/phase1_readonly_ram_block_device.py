"""One opt-in genuine SDK object for the read-only RAM nub; never instantiate it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import phase1_iostorage_declaration as sdk_probe
from user_instruction_diagnostics import summarize

ROOT = sdk_probe.ROOT
PORT = ROOT / 'note10/xnu26'
OUTPUT = ROOT / 'note10/private/v202-readonly-ram-provider-once'
CLASS = 'Note10ReadOnlyRAMBlockDevice'
MODE = 'readonly_ram_provider_object'
SCHEMA = 'note10-v202-readonly-ram-nub-target-result-v1'
FILES = ('note10/xnu26/note10_readonly_ram_block_device.h',
         'note10/xnu26/note10_readonly_ram_block_device.cpp',
         'note10/xnu26/readonly_ram_block_device_fixture.cpp',
         'note10/xnu26/readonly_ram_block_device_fixture_support.h',
         'note10/xnu26/phase1_readonly_ram_block_device.py',
         '.github/workflows/note10-phase1-iostorage-declaration-pc.yml',
         'note10/xnu26/phase1_iostorage_declaration.py',
         'note10/xnu26/note10_iostorage_pio_bridge.h',
         'note10/xnu26/user_instruction_diagnostics.py')
AUTHORITY = dict(registered_provider=False, active_transport_owner=False, runtime_IOKit_verified=False,
                 runtime_backing_owner_verified=False, native_kernel_contains_new_nub=False,
                 hardware_verified=False, physical_ready=False, native_activation=False,
                 device_input_admitted=False, firmware_abi_verified=False)
CAP = 1048576

def require(ok, reason):
    if not ok: raise ValueError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def source_read(path):
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= CAP, 'bounded_source')
    with path.open('rb') as stream: raw = stream.read(CAP + 1)
    require(len(raw) == path.stat().st_size <= CAP, 'source_extent')
    return raw

def fixture_headers(directory):
    for relative in ('IOKit/storage/IOBlockStorageDevice.h', 'IOKit/storage/IOStorage.h', 'IOKit/IOLocks.h'):
        target = directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('#include "readonly_ram_block_device_fixture_support.h"\n')

def fixture_argv(compiler, include, output):
    return [str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-pthread', '-DKERNEL=1',
            '-I', str(include), '-I', str(PORT), str(PORT / 'note10_readonly_ram_block_device.cpp'),
            str(PORT / 'readonly_ram_block_device_fixture.cpp'), '-o', str(output)]

def target_argv(include_flags, output):
    return ['xcrun', '--sdk', 'macosx', 'clang', *sdk_probe.COMPILE_FLAGS[:-1], *include_flags,
            '-O2', '-c', str(PORT / 'note10_readonly_ram_block_device.cpp'), '-o', str(output)]

def symbol_names(raw, returncode):
    require(returncode == 0 and len(raw) <= 131072, 'nm_process_or_cap')
    try: names = raw.decode('utf-8').splitlines()
    except UnicodeError: raise ValueError('nm_utf8') from None
    require(len(names) <= 512 and len(set(names)) == len(names) and
            all(re.fullmatch(r'[A-Za-z_.$][A-Za-z0-9_.$]{0,383}', name) for name in names), 'nm_name_shape')
    return sorted(names)

def compile_object(result, output):
    context = sdk_probe.public_sdk_context(result, 'provider_object')
    require(context is not None, 'sdk_headers_missing')
    sdk, kernel = context
    for name in ('IOKit/IOLocks.h', 'libkern/c++/OSObject.h'):
        path = next((base / name for base in (kernel, sdk / 'usr/include') if (base / name).is_file()), None)
        require(path is not None, 'new_sdk_header_missing')
        result['sdk_header_sha256'][name] = sha(source_read(path))
    result['sdk_header_provenance'] = 'Actual same-job Kernel.framework SDK headers; new lock/OSObject digests are observations, not an invented prior admission.'
    with tempfile.TemporaryDirectory(prefix='note10-ram-nub-') as temporary:
        work = Path(temporary)
        include = work / 'include'
        result.update(stage='pinned-archive-headers', archive_fetch_attempts=1)
        sdk_probe.stage_headers(include)
        result.update(archive_verified=True, archive_sha256=sdk_probe.ARCHIVE_SHA,
                      archive_header_sha256=sdk_probe.HEADERS)
        obj = work / 'readonly-ram-nub.o'
        flags = ['-isysroot', str(sdk), '-I', str(include), '-isystem', str(kernel),
                 '-isystem', str(sdk / 'usr/include')]
        argv = target_argv(flags, obj)
        result.update(stage='new-target-compile', target_object_compile_attempts=1,
                      compiler_argv_sha256=sha(json.dumps(argv, separators=(',', ':')).encode()))
        done = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=90)
        (output / 'compiler.internal.log').write_bytes(done.stdout + done.stderr)
        result['compiler_returncode'] = done.returncode
        result['compiler_diagnostics'] = summarize(done.stderr, {str(PORT): 'port', str(work): 'work', str(sdk): 'SDK'})
        require(done.returncode == 0, 'target_compile_returncode')
        result.update(stage='new-object-header', new_object_raw_reads=1)
        raw = source_read(obj)
        require(len(raw) >= 32 and struct.unpack_from('<4I', raw) == (0xfeedfacf, 0x100000c, 0, 1), 'plain_arm64_object')
        result.update(object_sha256=sha(raw), object_bytes=len(raw))
        views = []
        result['stage'] = 'new-object-symbols'
        for suffix, options in (('defined', ['-g', '-U', '-j']), ('undefined', ['-u', '-j'])):
            result['new_object_nm_views'] += 1
            view = subprocess.run(['xcrun', '--sdk', 'macosx', 'nm', *options, str(obj)],
                                  cwd=ROOT, capture_output=True, timeout=30)
            (output / (suffix + '.internal.log')).write_bytes(view.stdout + view.stderr)
            views.append(symbol_names(view.stdout, view.returncode))
        defined, undefined = views
        vtable = f'__ZTV{len(CLASS)}{CLASS}'
        metaclass = f'__ZN{len(CLASS)}{CLASS}10gMetaClassE'
        prefix = f'__ZN{len(CLASS)}{CLASS}16doAsyncReadWriteE'
        entries = [name for name in defined if name.startswith(prefix)]
        require(vtable in defined and metaclass in defined and len(entries) == 1, 'concrete_nub_symbols')
        require(sdk_probe.PROVIDER_BRIDGE_IMPORT in undefined and
                all(name in undefined for name in ('_IOLockAlloc', '_IOLockFree', '_IOLockLock', '_IOLockUnlock')) and
                any('IOBlockStorageDevice' in name for name in undefined), 'real_bridge_base_lock_imports')
        result.update(passed=True, stage='complete', target_object_verified=True, pure_virtual_interface_complete=True,
                      bridge_import_verified=True, lock_imports_verified=True, defined_external_symbols=defined,
                      undefined_external_symbols=undefined, read_entry_symbol=entries[0],
                      defined_vtable=vtable, defined_metaclass=metaclass)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    head, run = sdk_probe.reviewed_identity()
    require(os.environ.get('N10_PROBE_MODE') == MODE and (ROOT / args.output).resolve() == OUTPUT and not OUTPUT.exists(),
            'exact_mode_fresh_output')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    result = dict(schema=SCHEMA, feature=MODE, source_head=head, run_id=run, run_attempt=1,
                  target='arm64-apple-ios26.5.2', scope='readonly-ram-nub-production-source-object-only',
                  source_sha256={name: sha(source_read(ROOT / name)) for name in FILES}, authority=AUTHORITY,
                  passed=False, stage='source-binding', target_object_compile_attempts=0,
                  target_object_verified=False, new_object_raw_reads=0, new_object_nm_views=0,
                  archive_fetch_attempts=0, old_tests_count=0, kernel_builds=0, kernel_links=0,
                  host_fixture_replays=0, device_operations=0)
    try: compile_object(result, OUTPUT)
    except Exception as error:
        known = {'nm_process_or_cap', 'nm_utf8', 'nm_name_shape', 'sdk_headers_missing', 'new_sdk_header_missing',
                 'target_compile_returncode', 'plain_arm64_object', 'concrete_nub_symbols', 'real_bridge_base_lock_imports',
                 'bounded_source', 'source_extent'}
        result.update(passed=False, failure_type=type(error).__name__,
                      failure_code=str(error) if str(error) in known else 'unclassified_' + result['stage'])
    (OUTPUT / 'result.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return 0 if result['passed'] else 1

# The normal build selects one provider; the older standalone SDK proof stays unchanged.
NUB_SOURCE = 'note10/xnu26/note10_readonly_ram_block_device.cpp'
NUB_HEADER = 'note10/xnu26/note10_readonly_ram_block_device.h'
NUB_PINS = {NUB_SOURCE: '0e006108e9ac088ce94439bb087f70e4c4646daaa74a8a341da272b8e8d22cd0',
            NUB_HEADER: '14ef1309e063789911190f6c7d4c7cdaa3b6ac9843ac195b9e4092c91be0ecbe'}
SDK_DELTA = {'IOKit/IOLocks.h': 'b8c590a5c31ba1efe08ca5eeb59ed03688eab3f7f42b0879470dbbf24df7d158',
             'libkern/c++/OSObject.h': '69783dc78e1a398b11c0f2dcd2147277425f68a7e5c655519ded056d5b57ed3b'}
NATIVE_PINS = {'iokit/Kernel/IOLocks.cpp': '964b5a2d17d74df20a9095a05df4574535a6b1be1cad2700831d5e66078d6134',
               'osfmk/kern/lock_mtx.c': 'f9aaba2582d18925fa927cec86d31afa6ab23cc4a9e21339ce18b0470fb4c0e0',
               'libkern/c++/OSMetaClass.cpp': '6a019c97676762721668b98c7400c61b8a61769b38e54cfd025c2984197be3ef'}
EXPORT_SHA = 'a2b4b40b7559a37ccb0d29efb5972e30c9dda6a3e56eb57c9120c2a7a8eda76d'
LOCK_ALIASES = {'_IOLockLock': '_lck_mtx_lock', '_IOLockUnlock': '_lck_mtx_unlock'}
PROFILE_KEY = 'readonly_ram_nub'
PROVENANCE_SCHEMA = 'note10-v204-readonly-ram-nub-symbol-provenance-v1'
NUB_VTABLE = '__ZTV28Note10ReadOnlyRAMBlockDevice'
NUB_META = '__ZN28Note10ReadOnlyRAMBlockDevice10gMetaClassE'
NUB_READ = '__ZN28Note10ReadOnlyRAMBlockDevice16doAsyncReadWriteEP18IOMemoryDescriptoryyP19IOStorageAttributesP19IOStorageCompletion'
BASE_VTABLE = '__ZTV20IOBlockStorageDevice'
BASE_META = '__ZN20IOBlockStorageDevice10gMetaClassE'
META_INSTANCE = '__ZNK11OSMetaClass19instanceConstructedEv'
REQUEST, RANGE = '_note10_iostorage_read_request', '_note10_iostorage_read_range'
NATIVE_AUTHORITY = dict(registered_provider=False, transport_instantiated=False,
    runtime_backing_owner_verified=False, runtime_IOKit_verified=False, firmware_abi_verified=False,
    native_activation=False, kernel_executed=False, physical_ready=False, new_device_input_admitted=False)


def selected_sources(enabled=False):
    require(type(enabled) is bool, 'nub_boolean_required')
    pins = dict(sdk_probe.CLOSURE_INPUT_SHA256)
    if enabled:
        del pins[sdk_probe.PROVIDER_SOURCE]
        pins.update(NUB_PINS)
    return pins


def profile():
    return dict(schema='note10-v204-readonly-ram-nub-selection-v1', provider=NUB_SOURCE,
                source_sha256=NUB_PINS, sdk_delta_sha256=SDK_DELTA,
                native_source_sha256=NATIVE_PINS, export_sha256=EXPORT_SHA)


def enabled(current):
    from current_native_kernel import digest
    producer, bindings = current['producer'], current['bindings']
    if PROFILE_KEY not in producer and PROFILE_KEY not in bindings:
        return False
    require(producer.get(PROFILE_KEY) == profile() and bindings.get(PROFILE_KEY) == digest(profile()),
            'exact_nub_selection_required')
    return True


def sdk_delta(sdk, kernel):
    observed = {}
    for name, expected in SDK_DELTA.items():
        path = next((base / name for base in (kernel, sdk / 'usr/include') if (base / name).is_file()), None)
        require(path is not None, 'nub_sdk_header_missing')
        observed[name] = sha(source_read(path))
        require(observed[name] == expected, 'nub_sdk_header_changed')
    return observed


def origin_specs():
    from phase1_iostorage_native_complete import COMPLETE_SYMBOL, MEMBER_SHA256
    specs = {symbol: ('@storage/' + Path(NUB_SOURCE).name, NUB_PINS[NUB_SOURCE], 'storage')
             for symbol in (NUB_VTABLE, NUB_META, NUB_READ)}
    specs.update({symbol: ('@storage/IOBlockStorageDevice.cpp', sdk_probe.BASE_MEMBER_SHA, 'storage')
                  for symbol in (BASE_VTABLE, BASE_META)})
    specs.update({sdk_probe.PROVIDER_BRIDGE_IMPORT: ('@storage/' + Path(sdk_probe.PIO_SOURCE).name,
                    sdk_probe.CLOSURE_INPUT_SHA256[sdk_probe.PIO_SOURCE], 'storage'),
                  COMPLETE_SYMBOL: ('@storage/IOStorage.cpp', MEMBER_SHA256, 'storage')})
    for symbol, name in ((REQUEST, 'note10_iostorage_read_request.c'), (RANGE, 'note10_iostorage_read_range.c')):
        specs[symbol] = ('@storage/' + name, sdk_probe.CLOSURE_INPUT_SHA256['note10/xnu26/' + name], 'storage')
    for symbol, source in (('_IOLockAlloc', 'iokit/Kernel/IOLocks.cpp'), ('_IOLockFree', 'iokit/Kernel/IOLocks.cpp'),
                           (META_INSTANCE, 'libkern/c++/OSMetaClass.cpp'),
                           ('_lck_mtx_lock', 'osfmk/kern/lock_mtx.c'), ('_lck_mtx_unlock', 'osfmk/kern/lock_mtx.c')):
        specs[symbol] = (source, NATIVE_PINS[source], 'native')
    return specs


def edges():
    from phase1_iostorage_native_complete import COMPLETE_SYMBOL
    pio = sdk_probe.PROVIDER_BRIDGE_IMPORT
    return ((NUB_READ, pio), (pio, REQUEST), (pio, COMPLETE_SYMBOL), (REQUEST, RANGE),
            (NUB_VTABLE, BASE_VTABLE), (NUB_META, BASE_META), (NUB_META, META_INSTANCE),
            *((NUB_READ, symbol) for symbol in ('_IOLockLock', '_IOLockUnlock')),
            (NUB_META, '_IOLockAlloc'), (NUB_META, '_IOLockFree'))


def begin():
    return dict(schema=PROVENANCE_SCHEMA, passed=False, object_provenance_verified=False,
                final_symbols_verified=False, native_kernel_contains_new_nub=False, **NATIVE_AUTHORITY)


def bind_origins(current, rows, defined, references, aliases, exports, observation):
    from current_native_kernel import digest
    require(enabled(current) and current['producer_id'] == digest(current['producer']) and
            current['input_binding'] == digest(current['bindings']), 'nub_current_identity')
    by_path = {row['object_path']: row for row in rows}
    require(len(by_path) == len(rows), 'nub_unique_object_paths')
    require(all('phase1_iostorage_provider_object' not in row['source'] for row in rows), 'nub_probe_absent')
    members = {}
    for symbol, (source, source_sha, category) in origin_specs().items():
        paths = defined.get(symbol, [])
        require(len(paths) == 1 and paths[0] in by_path and symbol not in aliases, 'nub_unique_genuine_origin')
        row = by_path[paths[0]]
        require(row['source'] == source and row['source_sha256'] == source_sha and row['category'] == category and
                row['passed'] is True and row['producer_id'] == current['producer_id'] and
                row['input_binding'] == current['input_binding'] and
                re.fullmatch('[0-9a-f]{64}', row['object_sha256']) is not None, 'nub_source_origin')
        if category == 'storage':
            require(row['storage_binding'] == current['storage']['binding'], 'nub_storage_origin')
        members[symbol] = {key: row[key] for key in
                          ('source', 'source_sha256', 'category', 'object_path', 'object_sha256')}
    require(exports.get('config/IOKit.exports') == EXPORT_SHA and
            all(aliases.get(name) == target and not defined.get(name) for name, target in LOCK_ALIASES.items()),
            'nub_exact_real_lock_aliases')
    require(all(members[caller]['object_path'] in references.get(callee, []) for caller, callee in edges()),
            'nub_real_reference_edges')
    observation.update(producer_id=current['producer_id'], input_binding=current['input_binding'],
        members=members, lock_aliases=dict(LOCK_ALIASES), export_sha256=EXPORT_SHA,
        reference_edges_verified=True, object_provenance_verified=True)


def final_symbols(text, linked, current, observation):
    from current_native_kernel import expected_objects
    values = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and re.fullmatch('[0-9a-fA-F]+', parts[0]) and parts[-2].isupper():
            values.setdefault(parts[-1], []).append(int(parts[0], 16))
    required = (*origin_specs(), *LOCK_ALIASES)
    require(enabled(current) and observation['object_provenance_verified'] is True and
            linked['link_succeeded'] is True and type(linked['returncode']) is int and linked['returncode'] == 0 and
            linked['object_count'] == expected_objects(current, storage=True) and
            all(len(values.get(name, [])) == 1 for name in required) and
            all(values[name] == values[target] for name, target in LOCK_ALIASES.items()) and
            not any('Note10RAMBlockProviderProbe' in name for name in values), 'nub_final_symbols')
    observation.update(passed=True, native_kernel_contains_new_nub=True, final_symbols_verified=True,
                       lock_alias_addresses_verified=True,
                       final_symbol_counts={name: 1 for name in required}, linked_objects=linked['object_count'])


def verify_profile(current, rows, storage, state, producer, link):
    from current_native_kernel import digest
    require(enabled(current) and
            storage['binding']['proof'].get(PROFILE_KEY) == profile() and
            storage['binding']['proof'].get('readonly_ram_sdk_delta_sha256') == SDK_DELTA, 'nub_storage_profile')
    proof = state[PROFILE_KEY]
    require(proof == producer[PROFILE_KEY] and proof['schema'] == PROVENANCE_SCHEMA and
            proof['producer_id'] == current['producer_id'] and proof['input_binding'] == current['input_binding'] and
            all(proof[key] is True for key in ('passed', 'object_provenance_verified', 'reference_edges_verified',
                'final_symbols_verified', 'native_kernel_contains_new_nub', 'lock_alias_addresses_verified')) and
            all(proof[key] is False for key in NATIVE_AUTHORITY) and
            type(proof['linked_objects']) is int and proof['linked_objects'] == link['object_count'] and
            proof['lock_aliases'] == LOCK_ALIASES and proof['export_sha256'] == EXPORT_SHA and
            proof['final_symbol_counts'] == {name: 1 for name in (*origin_specs(), *LOCK_ALIASES)} and
            all(type(value) is int for value in proof['final_symbol_counts'].values()), 'nub_static_provenance')
    require(set(proof['members']) == set(origin_specs()), 'nub_exact_origins')
    all_rows = rows + storage['units']
    for symbol, (source, source_sha, category) in origin_specs().items():
        matches = [row for row in all_rows if row['source'] == source]
        require(len(matches) == 1 and matches[0]['source_sha256'] == source_sha and matches[0]['category'] == category and
                proof['members'][symbol] == {key: matches[0][key] for key in
                    ('source', 'source_sha256', 'category', 'object_path', 'object_sha256')}, 'nub_retained_origin')
    aliases = state['alias_evidence']
    require(aliases['source_exports_sha256'].get('config/IOKit.exports') == EXPORT_SHA and
            all(aliases['aliases'].get(name) == target for name, target in LOCK_ALIASES.items()) and
            storage['binding']['binding'] == digest(storage['binding']['proof']), 'nub_retained_aliases')


if __name__ == '__main__':
    raise SystemExit(main())
