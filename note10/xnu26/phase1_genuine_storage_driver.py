"""One genuine Apple storage caller object and its required family IIG header."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import struct
import subprocess
import tempfile
import urllib.request

import phase1_iostorage_declaration as sdk
from user_instruction_diagnostics import summarize

ROOT = sdk.ROOT
PORT = ROOT / 'note10/xnu26'
MODE = 'genuine_storage_driver_object'
SCHEMA = 'note10-v205-genuine-storage-driver-target-result-v1'
OUTPUT = ROOT / 'note10/private/v205-genuine-storage-driver-once'
FILES = ('note10/xnu26/phase1_genuine_storage_driver.py', 'note10/xnu26/test_genuine_storage_driver.py',
         '.github/workflows/note10-phase1-iostorage-declaration-pc.yml',
         'note10/xnu26/phase1_iostorage_declaration.py', 'note10/xnu26/user_instruction_diagnostics.py',
         'note10/inspect_macho.py')
CAP, TEXT_CAP, OBJECT_CAP, NM_CAP, TOOL_CAP = 1048576, 524288, 4194304, 262144, 536870912
TARGET = 'arm64-apple-ios26.5.2'
MIN_OS = (26 << 16) | (5 << 8) | 2
FRAMEWORK = 'BlockStorageDeviceDriverKit'
FAMILY_DEFINITION = 'BlockStorageDeviceDriverKit/IOUserBlockStorageDevice.iig'
PERSONALITY = {'IOClass': 'IOBlockStorageDriver', 'IOPropertyMatch': {'device-type': 'Generic'},
               'IOProviderClass': 'IOBlockStorageDevice'}
SDK_DELTA = ('IOKit/IODeviceTreeSupport.h', 'IOKit/IOKitKeys.h', 'IOKit/IOMapper.h',
             'IOKit/IOSubMemoryDescriptor.h', 'IOKit/pwr_mgt/RootDomain.h',
             'IOKit/perfcontrol/IOPerfControl.h', 'kern/energy_perf.h', 'kern/thread_call.h',
             'kern/queue.h', 'libkern/OSAtomic.h', 'AssertMacros.h', 'stdatomic.h',
             'DriverKit/OSObject.h', 'DriverKit/IOService.h', 'DriverKit/IOMemoryDescriptor.h')
REUSED_HEADERS = {'IOKit/IOLocks.h': 'b8c590a5c31ba1efe08ca5eeb59ed03688eab3f7f42b0879470dbbf24df7d158',
                  'libkern/c++/OSObject.h': '69783dc78e1a398b11c0f2dcd2147277425f68a7e5c655519ded056d5b57ed3b'}
TOOLS = {'clang': 'd2e4bf622758eee1bf7267c060497fb2c41e098d37b0fca8be73898dc7e14eda',
         'iig': '308a5dd31cf4b1293bc93897040c22aba874834ddd2cd1d5e25a4a2d90b077a1'}
CLASS_VTABLE = '__ZTV20IOBlockStorageDriver'
CLASS_META = '__ZN20IOBlockStorageDriver10gMetaClassE'
METHODS = ('__ZN20IOBlockStorageDriver14executeRequestE', '__ZN20IOBlockStorageDriver4readE',
           '__ZN20IOBlockStorageDriver5writeE')
LOCK_ALIASES = {'_IOLockLock': '_lck_mtx_lock', '_IOLockUnlock': '_lck_mtx_unlock'}
LOCK_IMPORTS = ('_IOLockAlloc', '_IOLockFree', '_IOLockLock', '_IOLockUnlock')
LOCK_PINS = {'iokit/Kernel/IOLocks.cpp': '964b5a2d17d74df20a9095a05df4574535a6b1be1cad2700831d5e66078d6134',
             'osfmk/kern/lock_mtx.c': 'f9aaba2582d18925fa927cec86d31afa6ab23cc4a9e21339ce18b0470fb4c0e0'}
EXPORT_SHA = 'a2b4b40b7559a37ccb0d29efb5972e30c9dda6a3e56eb57c9120c2a7a8eda76d'
AUTHORITY = dict(new_driver_linked_in_native_kernel=False, registered_provider=False, matching_executed=False,
                 transport_instantiated=False, runtime_backing_owner_verified=False,
                 concrete_nub_dispatch_verified=False, runtime_IOKit_verified=False, firmware_abi_verified=False,
                 native_activation=False, kernel_executed=False, physical_ready=False, new_device_input_admitted=False,
                 new_RAM_MMIO_MMU_or_CPU_operation=False)
FAMILY_MEMBERS = {'BlockStorageDeviceDriverKit/IOUserBlockStorageDevice.iig': (6150, '6c595e4170a2177404b1acbeefa0fa3c83d367720c2e2f7ae04fe55aca556bd0'), 'IOBlockStorageDriver.cpp': (118245, '2b592995cdd38f3c314940f6f85ac0b8f8523864332b9cd74ee6e9d7710b752e'), 'IOBlockStorageDriver.h': (59282, '61b9dee6666f0569d82089454e1cabb02e8beeabc3c1a1d8095d6757bd701bcd'), 'IOBlockStoragePerfControlExports.h': (1630, 'ee74993d98e760bdcc57e4b5b71f5d8c987e1d2978d8021038d14e26b0bee9e7'), 'IORequestsPool.h': (1536, '9b92f88c419615c2b8ca6e900f753be58355dfc3c07731ec8699c27a1133fb19'), 'IOUserBlockStorageDevice_kext.h': (5495, '7fc745b48f9e83e453ab73a800926be918e212a187d248214a055ae8971d0d4f'), 'Info.plist': (5572, 'edefe0f8c9d9cfd3024438086d41fda2fc92f2ccac68ca5f9d9425156abd93bf')}
XNU_TEXT = {'DriverKit/IOService.iig': (25192, '874c48d99a6663f339a21479d05fd39d2fdca0f6fdf0c1515d8d71391826363a', 'https://raw.githubusercontent.com/apple-oss-distributions/xnu/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/iokit/DriverKit/IOService.iig'), 'DriverKit/IOMemoryDescriptor.iig': (7151, '45df15591122b1f8cae88b974fe5fb8240213a6d3c6a56e0af85d9d5b85a86ba', 'https://raw.githubusercontent.com/apple-oss-distributions/xnu/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/iokit/DriverKit/IOMemoryDescriptor.iig'), 'DriverKit/OSObject.iig': (10598, 'bcd00a8dfda6bbb511156ca23cb9a6b1685a828c6b91bb589144bba91215aca1', 'https://raw.githubusercontent.com/apple-oss-distributions/xnu/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/iokit/DriverKit/OSObject.iig'), 'DriverKit/IOReturn.h': (9741, '4767dd8a847d4b7dcff0b74c7a67013f0462f3ea6313e5a483f49fe046f93ab1', 'https://raw.githubusercontent.com/apple-oss-distributions/xnu/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/iokit/DriverKit/IOReturn.h')}



def require(ok, code):
    if not ok:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def read(path, cap=CAP):
    require(path.resolve() == path and not path.is_symlink() and path.is_file() and
            0 < path.stat().st_size <= cap, 'ordinary_bounded_input')
    with path.open('rb') as stream:
        raw = stream.read(cap + 1)
    require(len(raw) == path.stat().st_size <= cap, 'bounded_input_extent')
    return raw


def validate_personality(value):
    require(type(value) is dict and value.get('IOKitPersonalities', {}).get('IOBlockStorageDriver') == PERSONALITY,
            'genuine_personality')
    return dict(PERSONALITY)


def header_frame(raw):
    path = ROOT / 'note10/inspect_macho.py'
    tree = ast.parse(read(path))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'header_commands']
    require(len(nodes) == 1 and not nodes[0].decorator_list, 'neutral_header_framer')
    scope = {'struct': struct}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    return scope['header_commands'](raw)


def target_header(raw, frame=header_frame):
    require(type(raw) is bytes and 32 <= len(raw) <= OBJECT_CAP, 'new_object_cap')
    header, commands = frame(raw)
    require(header[:4] == (0xfeedfacf, 0x100000c, 0, 1), 'plain_arm64_caller_object')
    deployment = []
    for off, kind, size in commands:
        if kind == 0x32:
            require(size >= 24 and size == 24 + struct.unpack_from('<I', raw, off + 20)[0] * 8,
                    'object_build_version_extent')
            deployment.append(struct.unpack_from('<II', raw, off + 8))
        elif kind == 0x25:
            require(size == 16, 'object_minimum_version_extent')
            deployment.append((2, struct.unpack_from('<I', raw, off + 8)[0]))
    require(deployment == [(2, MIN_OS)], 'object_ios_deployment')
    return dict(cpu=header[1], subtype=header[2], filetype=header[3], platform=2, minimum_os=MIN_OS)


def symbol_names(raw, returncode):
    require(type(returncode) is int and returncode == 0 and type(raw) is bytes and len(raw) <= NM_CAP,
            'new_symbol_view_process_cap')
    try:
        names = raw.decode('utf-8').splitlines()
    except UnicodeError:
        raise ValueError('new_symbol_view_utf8') from None
    require(len(names) <= 2048 and len(set(names)) == len(names) and
            all(re.fullmatch(r'(?:_[A-Za-z0-9_.$]{1,511}|section\$(?:start|end)\$[A-Za-z0-9_$]{1,120})', name)
                for name in names), 'new_symbol_view_names')
    return sorted(names)


def caller_symbols(defined, undefined):
    require(type(defined) is list and type(undefined) is list and defined and undefined and
            len(set(defined)) == len(defined) and len(set(undefined)) == len(undefined) and
            not set(defined) & set(undefined) and CLASS_VTABLE in defined and CLASS_META in defined and
            all(sum(name.startswith(prefix) for name in defined) == 1 for prefix in METHODS),
            'genuine_driver_definitions')
    require(set(LOCK_IMPORTS) <= set(undefined) and '_io_rate_update' in undefined and
            '__ZN24IOUserBlockStorageDevice10gMetaClassE' in undefined and
            sum(name.startswith('__ZN24IOUserBlockStorageDevice20getPerfControlClientE') for name in undefined) == 1,
            'genuine_driver_open_imports')
    return {prefix: next(name for name in defined if name.startswith(prefix)) for prefix in METHODS}


def shared_import_origins(undefined, retained):
    proof = retained['readonly_ram_nub']
    require(retained['source_head'] == '05018bdb34fef65b1c8f040bf487e4e5e7ae464f' and
            type(retained['run_id']) is int and retained['run_id'] == 43016946791 and
            retained['kernel_retained'] is True and retained['underlying_provenance_verified'] is True and
            retained['fresh_kernel_hash'] is False and retained['fresh_kernel_bytes_verified'] is False and
            proof['schema'] == 'note10-v204-readonly-ram-nub-symbol-provenance-v1' and
            all(proof[key] is True for key in ('passed', 'object_provenance_verified', 'final_symbols_verified',
                'native_kernel_contains_new_nub', 'lock_alias_addresses_verified')) and
            all(proof[key] is False for key in ('registered_provider', 'transport_instantiated',
                'runtime_backing_owner_verified', 'runtime_IOKit_verified', 'firmware_abi_verified',
                'native_activation', 'kernel_executed', 'physical_ready', 'new_device_input_admitted')) and
            proof['lock_aliases'] == LOCK_ALIASES and proof['export_sha256'] == EXPORT_SHA and
            set(LOCK_IMPORTS) <= set(undefined), 'accepted204_static_origin_evidence')
    matches = {}
    for name in undefined:
        target = LOCK_ALIASES.get(name, name)
        if target not in proof['members']:
            continue
        member = proof['members'][target]
        require(set(member) == {'source', 'source_sha256', 'category', 'object_path', 'object_sha256'} and
                digest(member['source_sha256']) and digest(member['object_sha256']) and
                type(proof['final_symbol_counts'][name]) is int and proof['final_symbol_counts'][name] == 1,
                'shared_origin_member')
        if name in LOCK_IMPORTS:
            source = 'osfmk/kern/lock_mtx.c' if name in LOCK_ALIASES else 'iokit/Kernel/IOLocks.cpp'
            require(member['source'] == source and member['source_sha256'] == LOCK_PINS[source] and
                    member['category'] == 'native', 'shared_lock_origin')
        matches[name] = dict(kind='export-alias' if name in LOCK_ALIASES else 'direct', target=target, member=member)
    require(set(LOCK_IMPORTS) <= set(matches), 'shared_four_lock_origins')
    unlinked = sorted(set(undefined) - set(matches))
    require(unlinked, 'open_imports_remain_explicit')
    return dict(existing_static_origin_associations=matches, additional_unlinked_imports=unlinked,
                all_imports_resolved=False, new_driver_linked_in_native_kernel=False,
                concrete_nub_dispatch_verified=False)


def validate_result(value, head, run, committed_sources):
    require(value['schema'] == SCHEMA and value['feature'] == MODE and value['source_head'] == head and
            type(value['run_id']) is int and value['run_id'] == run and type(value['run_attempt']) is int and
            value['run_attempt'] == 1 and value['passed'] is True and value['stage'] == 'complete' and
            value['target'] == TARGET and value['all_imports_resolved'] is False and
            value['source_sha256'] == committed_sources and set(committed_sources) == set(FILES) and
            all(digest(h) for h in committed_sources.values()) and value['authority'] == AUTHORITY and
            all(type(v) is bool for v in value['authority'].values()), 'exact_current_driver_result')
    require(all(type(value[k]) is int and value[k] == n for k, n in dict(archive_fetch_attempts=1,
                family_members_staged=7, old_header_dependencies_staged=5, source_text_GETs=4,
                IIG_attempts=1, IIG_returncode=0, target_object_compile_attempts=1, compiler_returncode=0,
                new_object_raw_reads=1, new_object_nm_views=2, tool_hash_reads=2, old_suites_executed=0,
                kernel_builds=0, kernel_links=0, device_operations=0).items()) and
            value['generated_impl_compiled'] is False and value['object_target_verified'] is True and
            type(value['object_bytes']) is int and 32 <= value['object_bytes'] <= OBJECT_CAP and
            digest(value['object_sha256']) and digest(value['generated_header_sha256']) and
            value['family_input_sha256'] == {name: row[1] for name, row in FAMILY_MEMBERS.items()} and
            value['XNU_input_sha256'] == {name: row[1] for name, row in XNU_TEXT.items()} and
            value['IIG_framework'] == FRAMEWORK and value['personality'] == PERSONALITY and
            value['public_sdk_baseline_sha256'] == sdk.CLOSURE_PUBLIC_SDK_SHA256 and
            value['sdk_reused_header_sha256'] == REUSED_HEADERS and
            set(value['sdk_new_header_sha256']) == set(SDK_DELTA) and
            all(digest(v) for v in value['sdk_new_header_sha256'].values()) and value['tool_sha256'] == TOOLS and
            value['object_target'] == dict(cpu=0x100000c, subtype=0, filetype=1, platform=2, minimum_os=MIN_OS) and
            all(type(v) is int for v in value['object_target'].values()),
            'one_genuine_caller_dependency_budget')
    require(value['method_symbols'] == caller_symbols(value['defined_external_symbols'], value['undefined_external_symbols']),
            'exact_observed_caller_methods')


def hash_tool(path):
    require(path.is_file() and 0 < path.stat().st_size <= TOOL_CAP, 'tool_stat_bound')
    hashed = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(CAP), b''):
            hashed.update(chunk)
    return hashed.hexdigest()


def checked_sdk(result):
    context = sdk.public_sdk_context(result, 'base_object')
    require(context is not None and result['sdk_version'] == '26.5', 'actual_sdk_baseline_required')
    root, kernel = context
    baseline = json.dumps(result['sdk_header_sha256'], sort_keys=True, separators=(',', ':')).encode()
    require(sha(baseline) == sdk.CLOSURE_PUBLIC_SDK_SHA256, 'same_sdk_baseline_digest')
    result['public_sdk_baseline_sha256'] = sha(baseline)
    result['sdk_reused_header_sha256'] = {}
    for name, expected in REUSED_HEADERS.items():
        path = next((base / name for base in (kernel, root / 'usr/include') if (base / name).is_file()), None)
        require(path is not None, 'existing_sdk_lock_owner_header_missing')
        observed = sha(read(path.resolve()))
        require(observed == expected, 'existing_sdk_lock_owner_header_changed')
        result['sdk_reused_header_sha256'][name] = observed
    result['sdk_new_header_sha256'], result['sdk_new_header_paths'] = {}, {}
    for name in SDK_DELTA:
        path = next((base / name for base in (kernel, root / 'usr/include') if (base / name).is_file()), None)
        if path is None:
            result['missing_sdk_header'] = name
            raise ValueError('new_required_sdk_header_missing')
        path = path.resolve()
        result['sdk_new_header_sha256'][name] = sha(read(path))
        result['sdk_new_header_paths'][name] = str(path)
    return root, kernel


def stage_inputs(work, result):
    include, family = work / 'include', work / 'family'
    family.mkdir()
    result.update(stage='family-source-admission', archive_fetch_attempts=1)
    with sdk.open_verified_archive() as archive:
        sdk.stage_storage_members(archive, include, None)
        result['old_header_dependencies_staged'] = len(sdk.HEADERS)
        for name, (size, expected) in FAMILY_MEMBERS.items():
            member = archive.getmember('IOStorageFamily-' + sdk.COMMIT + '/' + name)
            require(member.isfile() and member.size == size <= TEXT_CAP, 'new_family_member_extent')
            with archive.extractfile(member) as stream:
                raw = stream.read(TEXT_CAP + 1)
            require(len(raw) == size and sha(raw) == expected, 'new_family_member_hash')
            path = family / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            if name in ('IOBlockStorageDriver.h', 'IOBlockStoragePerfControlExports.h'):
                (include / 'IOKit/storage' / name).write_bytes(raw)
            result['family_members_staged'] += 1
    result['personality'] = validate_personality(plistlib.loads(read(family / 'Info.plist', TEXT_CAP)))
    result['family_input_sha256'] = {name: row[1] for name, row in FAMILY_MEMBERS.items()}
    xnu = work / 'xnu-inputs/iokit'
    result['stage'] = 'IIG-public-input-admission'
    for name, (size, expected, url) in XNU_TEXT.items():
        result['source_text_GETs'] += 1
        with urllib.request.urlopen(url, timeout=30) as response:
            raw = response.read(TEXT_CAP + 1)
        require(len(raw) == size <= TEXT_CAP and sha(raw) == expected and b'\0' not in raw,
                'exact_public_IIG_input')
        path = xnu / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    result['XNU_input_sha256'] = {name: row[1] for name, row in XNU_TEXT.items()}
    return include, family, xnu


def tool_call(argv, output, label, result, roots):
    done = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=120)
    require(len(done.stdout) <= NM_CAP and len(done.stderr) <= NM_CAP, 'bounded_tool_diagnostics')
    (output / (label + '.internal.log')).write_bytes(done.stdout + done.stderr)
    result[label + '_argv_sha256'] = sha(json.dumps(argv, separators=(',', ':')).encode())
    result[label + '_diagnostics'] = summarize(done.stderr, roots)
    return done


def produce(result, output):
    result['stage'] = 'SDK-required-header-preflight'
    root, kernel = checked_sdk(result)
    result['stage'] = 'tool-binding'
    result['tool_sha256'], result['tool_paths'] = {}, {}
    for name, expected in TOOLS.items():
        path = Path(sdk.read_command(['xcrun', '-f', name])).resolve()
        result['tool_hash_reads'] += 1
        observed = hash_tool(path)
        require(observed == expected, 'same_compiler_IIG_binary_identity')
        result['tool_sha256'][name], result['tool_paths'][name] = observed, str(path)
    result['compiler_version'] = sdk.read_command([result['tool_paths']['clang'], '--version']).splitlines()[0]
    result['IIG_version_basis'] = 'Exact accepted binary digest; no speculative version CLI.'
    with tempfile.TemporaryDirectory(prefix='note10-genuine-storage-driver-') as temporary:
        work = Path(temporary).resolve()
        include, family, xnu = stage_inputs(work, result)
        generated = work / 'generated'
        generated.mkdir()
        header, impl = generated / 'IOUserBlockStorageDevice.h', generated / 'IOUserBlockStorageDevice.iig.cpp'
        roots = {str(ROOT): 'project', str(work): 'work', str(root): 'SDK'}
        argv = ['xcrun', '--sdk', 'macosx', 'iig', '--def', str(family / FAMILY_DEFINITION),
                '--header', str(header), '--impl', str(impl), '--framework-name', FRAMEWORK, '--',
                '-I' + str(xnu), '-isystem', str(kernel), '-isystem', str(root / 'usr/include'),
                '-isysroot', str(root), '-x', 'c++', '-std=gnu++2b', '-D__IIG=1',
                '-DDRIVERKIT_PRIVATE=1', '-DPRIVATE_WIFI_ONLY=1']
        result.update(stage='new-family-IIG-header', IIG_attempts=1, IIG_framework=FRAMEWORK)
        done = tool_call(argv, output, 'IIG', result, roots)
        result['IIG_returncode'] = done.returncode
        require(done.returncode == 0, 'new_family_IIG_returncode')
        result['generated_header_sha256'] = sha(read(header))
        require(impl.is_file() and 0 < impl.stat().st_size <= CAP, 'IIG_side_output_extent')
        result['generated_impl_compiled'] = False
        obj = work / 'genuine-storage-driver.o'
        argv = ['xcrun', '--sdk', 'macosx', 'clang', *sdk.COMPILE_FLAGS[:-1], '-isysroot', str(root),
                '-I', str(generated), '-I', str(family), '-I', str(include), '-isystem', str(kernel),
                '-isystem', str(root / 'usr/include'), '-O2', '-c', str(family / 'IOBlockStorageDriver.cpp'),
                '-o', str(obj)]
        result.update(stage='new-genuine-caller-compile', target_object_compile_attempts=1)
        done = tool_call(argv, output, 'compiler', result, roots)
        result['compiler_returncode'] = done.returncode
        require(done.returncode == 0, 'new_genuine_caller_returncode')
        result.update(stage='new-caller-object-target', new_object_raw_reads=1)
        raw = read(obj, OBJECT_CAP)
        result.update(object_bytes=len(raw), object_sha256=sha(raw), object_target=target_header(raw),
                      object_target_verified=True)
        result['stage'] = 'new-caller-symbols'
        views = []
        for name, options in (('defined', ['-g', '-U', '-j']), ('undefined', ['-u', '-j'])):
            result['new_object_nm_views'] += 1
            done = tool_call(['xcrun', '--sdk', 'macosx', 'nm', *options, str(obj)], output, name, result, roots)
            views.append(symbol_names(done.stdout, done.returncode))
        defined, undefined = views
        result.update(defined_external_symbols=defined, undefined_external_symbols=undefined,
                      method_symbols=caller_symbols(defined, undefined), passed=True, stage='complete',
                      all_imports_resolved=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    head, run = sdk.reviewed_identity()
    require(os.environ.get('N10_PROBE_MODE') == MODE and (ROOT / args.output).resolve() == OUTPUT and
            not OUTPUT.exists(), 'exact_mode_and_fresh_output')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    result = dict(schema=SCHEMA, feature=MODE, source_head=head, run_id=run, run_attempt=1, target=TARGET,
        source_sha256={name: sha(read(ROOT / name)) for name in FILES}, authority=AUTHORITY,
        passed=False, stage='source-binding', archive_fetch_attempts=0, family_members_staged=0,
        old_header_dependencies_staged=0, source_text_GETs=0, IIG_attempts=0,
        target_object_compile_attempts=0, new_object_raw_reads=0, new_object_nm_views=0, tool_hash_reads=0,
        generated_impl_compiled=False, object_target_verified=False, all_imports_resolved=False,
        old_suites_executed=0, kernel_builds=0, kernel_links=0, device_operations=0)
    try:
        produce(result, OUTPUT)
    except Exception as error:
        code = str(error)
        result.update(passed=False, failure_type=type(error).__name__,
                      failure_code=code if re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,95}', code) else 'unclassified_' + result['stage'])
    (OUTPUT / 'result.json').write_bytes((json.dumps(result, sort_keys=True, indent=2) + '\n').encode())
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
