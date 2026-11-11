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

if __name__ == '__main__':
    raise SystemExit(main())
