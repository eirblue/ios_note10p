"""Check public IOStorage sources against the actual macOS SDK."""
import argparse
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tarfile
import tempfile
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'note10/xnu26/phase1_iostorage_declaration.cpp'
PIO_SOURCE = 'note10/xnu26/note10_iostorage_pio_bridge.cpp'
PROVIDER_SOURCE = 'note10/xnu26/phase1_iostorage_provider_object.cpp'
NATIVE_INPUTS_SOURCE = 'note10/xnu26/phase1_iostorage_native_inputs.py'
NATIVE_COMPLETE_SOURCE = 'note10/xnu26/phase1_iostorage_native_complete.py'
USER_FETCH_SOURCE = 'note10/xnu26/phase1_user_instruction_fetch.py'
USER_BRANCH_CLOSURE_SOURCE = 'note10/xnu26/phase1_user_auth_branch_closure.py'
MEMDEV_WIDE_SOURCE = 'note10/xnu26/phase1_memdev_wide_extent.py'
NATIVE_INPUTS_SHA256 = 'bf34f56e47bf5a05119ad45d6e00fdd7d6972076aad02f4788459b0c112fa126'
CLOSURE_INPUT_SHA256 = {
    NATIVE_COMPLETE_SOURCE: 'c6ac1a8685972aabd5eabdf6aa8d66d41e100e895a5212330c77f507f67f3d3c',
    PROVIDER_SOURCE: 'ac252306b4dd3faea053f9b171663d3f17794b9fa8790aa4c88b21c10dda87b7',
    PIO_SOURCE: '56bbcdb885b04650d4216cc37c06e148fd626fcfc919a7bfe62da8ab2bb52ec0',
    'note10/xnu26/note10_iostorage_pio_bridge.h': 'f57c49f687c80a672b980fe3d74a03968311724f8871a65c53fd67b124c869d1',
    'note10/xnu26/note10_iostorage_read_range.c': '12b9de8c5e7c59b0e2df4deec0e109043d53ee5f7dd45653ce899d0f17ae38a2',
    'note10/xnu26/note10_iostorage_read_range.h': '61bd6d3741137139cbb00280334c763dbe85431483cbee8e31270c61361df2a3',
    'note10/xnu26/note10_iostorage_read_request.c': '7b5fd68db13eb27ff35cf3f3f70fd9cda4cf76bc414867e8b802189efb6a6815',
    'note10/xnu26/note10_iostorage_read_request.h': 'bedab328a94426f0409b3617d80746d3bf5ee76a03e2bcc2537808092f8d2f15',
}
CLOSURE_PUBLIC_SDK_SHA256 = 'd86ae8d761c1b5788400912f5007504d3a7d32b3c70647a23e61fe48f7bd2007'
PROVIDER_CLASS = 'Note10RAMBlockProviderProbe'
PROVIDER_BRIDGE_IMPORT = '__Z25note10_iostorage_pio_readPKvyyP18IOMemoryDescriptoryyPK19IOStorageCompletion'
PROVIDER_METACLASS_SHA = '030784b3b7962124b69d855d5ac20323b78522a3be5f9806908baa0ef9126494'
PIO_INPUTS = (
    'note10/xnu26/note10_iostorage_pio_bridge.h',
    'note10/xnu26/note10_iostorage_read_request.h',
    'note10/xnu26/note10_iostorage_read_range.h',
)
PIO_LINK_C_SOURCES = (
    'note10/xnu26/note10_iostorage_read_range.c',
    'note10/xnu26/note10_iostorage_read_request.c',
)
PIO_SDK_PINS = {
    'IOKit/IOMemoryDescriptor.h': '69b98b0114396328b5c931794f071fc1c115aac798a1734c03562a1846825afd',
    'IOKit/IOTypes.h': '42fb65aa1ba30e15fb746a2ad8e75e92dff78f8d0430469ce08e9ba6387601b1',
}
WORKFLOW = '.github/workflows/note10-phase1-iostorage-declaration-pc.yml'
REPOSITORY = 'eirblue/ios_note10p'
JOB = 'iostorage-public-declaration'
COMMIT = '7edb88fbae296fb7c8ce2f64e115e116e566d51c'
ARCHIVE_URL = 'https://codeload.github.com/apple-oss-distributions/IOStorageFamily/tar.gz/' + COMMIT
ARCHIVE_BYTES = 1361346
ARCHIVE_SHA = '2a2b85c3350157e5e93f945c8729b8b8915ff5dc26a284bedc892af43519f413'
BASE_MEMBER = 'IOBlockStorageDevice.cpp'
BASE_MEMBER_BYTES = 7912
BASE_MEMBER_SHA = '91391448f3abced8238f71cce6b9f1062bd22e43994243e25c86df3e73ffd848'
BASE_REQUIRED_SYMBOLS = (
    '__ZN20IOBlockStorageDevice10gMetaClassE',
    '__ZN20IOBlockStorageDevice11requestIdleEv',
    '__ZN20IOBlockStorageDevice13doSetPriorityEP26IOBlockStorageDeviceExtentjh',
    '__ZN20IOBlockStorageDevice13doSynchronizeEyyj',
    '__ZN20IOBlockStorageDevice13setPropertiesEP8OSObject',
    '__ZN20IOBlockStorageDevice18doSynchronizeCacheEv',
    '__ZN20IOBlockStorageDevice18getWriteCacheStateEPb',
    '__ZN20IOBlockStorageDevice18setWriteCacheStateEb',
    '__ZN20IOBlockStorageDevice20doGetProvisionStatusEyyPjP35IOBlockStorageProvisionDeviceExtenty',
    '__ZN20IOBlockStorageDevice4initEP12OSDictionary',
    '__ZN20IOBlockStorageDevice7doUnmapEP26IOBlockStorageDeviceExtentjj',
    '__ZN20IOBlockStorageDeviceC2EPK11OSMetaClass',
    '__ZN20IOBlockStorageDeviceD2Ev',
    '__ZNK20IOBlockStorageDevice11getPropertyEPK8OSSymbol',
)
HEADERS = {
    'IOBlockStorageDevice.h': 'afe6609327355c84a70f764c55291d41931e47dedbfb49dc9a2b3601902cdd9c',
    'IOMedia.h': 'f8d96b002ec37bdc32e8b715394b8324e399f73ede88ac5d2d9770780e7a3bab',
    'IOStorage.h': '28a83281984b4ba81e1bbb2455b6e55c3881095de06c5b92c32d1b64536da123',
    'IOStorageDeviceCharacteristics.h': 'eb054c1ac78d6d893b1c60221aeedad4edddec735836a76924aef722469b2be4',
    'IOStorageProtocolCharacteristics.h': '704a61da21588227bda6e0fdacadf24e763fe36ff2e215da47b7d922cd619649',
}
SDK_HEADERS = (
    'TargetConditionals.h', 'IOKit/IOTypes.h', 'IOKit/IOMemoryDescriptor.h', 'IOKit/IOMessage.h',
    'IOKit/IOService.h', 'IOKit/assert.h', 'libkern/c++/OSMetaClass.h', 'sys/kernel_types.h',
)
BASE_SDK_HEADERS = ('IOKit/IOLib.h', 'IOKit/IOUserClient.h', 'IOKit/system.h', 'kern/task.h')
TARGET = 'arm64-apple-ios26.5.2'
COMPILE_FLAGS = (
    '--target=' + TARGET, '-std=gnu++2b', '-mkernel', '-fapple-kext', '-fsized-deallocation',
    '-ffreestanding', '-fno-builtin', '-fno-common', '-fblocks', '-nostdlibinc', '-nostdinc++',
    '-DKERNEL=1', '-ferror-limit=8', '-fsyntax-only',
)
C_OBJECT_FLAGS = (
    '--target=' + TARGET, '-std=c11', '-mkernel', '-ffreestanding', '-fno-builtin',
    '-fno-common', '-nostdlibinc', '-DKERNEL=1', '-ferror-limit=8',
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read_command(argv):
    return subprocess.check_output(argv, cwd=ROOT, stderr=subprocess.DEVNULL, timeout=30, text=True).strip()


def reviewed_identity():
    env = os.environ
    head = env.get('N10_EXPECTED_SOURCE_HEAD', '')
    run_id = env.get('GITHUB_RUN_ID', '')
    require(sys.platform == 'darwin' and env.get('GITHUB_ACTIONS') == 'true' and
            re.fullmatch('[0-9a-f]{40}', head) and re.fullmatch('[1-9][0-9]*', run_id) and
            env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' and env.get('GITHUB_RUN_ATTEMPT') == '1' and
            env.get('GITHUB_SHA') == env.get('GITHUB_WORKFLOW_SHA') == head and
            env.get('GITHUB_REPOSITORY') == REPOSITORY and env.get('GITHUB_JOB') == JOB and
            env.get('GITHUB_WORKFLOW_REF') == REPOSITORY + '/' + WORKFLOW + '@refs/heads/main' and
            read_command(['git', 'rev-parse', 'HEAD']) == head, 'reviewed manual macOS first attempt required')
    return head, int(run_id)


def open_verified_archive():
    with urllib.request.urlopen(ARCHIVE_URL, timeout=30) as response:
        raw = response.read(ARCHIVE_BYTES + 1)
    require(len(raw) == ARCHIVE_BYTES and sha(raw) == ARCHIVE_SHA, 'public IOStorageFamily archive pin differs')
    return tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz')


def stage_storage_members(archive, include, base_source):
    storage = include / 'IOKit/storage'
    storage.mkdir(parents=True)
    for name, digest in HEADERS.items():
        member = archive.getmember('IOStorageFamily-' + COMMIT + '/' + name)
        require(member.isfile() and 0 < member.size <= 1024 * 1024, 'expected ordinary bounded archive header')
        with archive.extractfile(member) as stream:
            data = stream.read()
        require(sha(data) == digest, 'public IOStorageFamily header pin differs')
        (storage / name).write_bytes(data)
    if base_source is not None:
        member = archive.getmember('IOStorageFamily-' + COMMIT + '/' + BASE_MEMBER)
        require(member.isfile() and member.size == BASE_MEMBER_BYTES, 'public base implementation size differs')
        with archive.extractfile(member) as stream:
            data = stream.read()
        require(sha(data) == BASE_MEMBER_SHA, 'public base implementation pin differs')
        base_source.write_bytes(data)


def stage_headers(include, base_source=None):
    with open_verified_archive() as archive:
        stage_storage_members(archive, include, base_source)


def require_arm64_object(path):
    with path.open('rb') as stream:
        magic, cpu, subtype, kind = struct.unpack('<4I', stream.read(16))
    require(magic == 0xfeedfacf and cpu == 0x0100000c and (subtype & 0xffffff) == 0 and kind == 1,
            'expected plain ARM64 Mach-O relocatable object')


def link_pio(result, work, compiler, includes):
    result['stage'] = 'pio-object-compile'
    objects = []
    returncodes = []
    result['object_compiler_returncodes'] = returncodes
    units = ((PIO_SOURCE, COMPILE_FLAGS[:-1]), *((source, C_OBJECT_FLAGS) for source in PIO_LINK_C_SOURCES))
    for source, flags in units:
        obj = work / (Path(source).stem + '.o')
        result['compile_attempts'] += 1
        call = subprocess.run([*compiler, *flags, *includes, '-O2', '-c', source, '-o', str(obj)],
                              cwd=ROOT, capture_output=True, timeout=60)
        returncodes.append(call.returncode)
        if call.returncode:
            return
        require_arm64_object(obj)
        objects.append(str(obj))
    result['compiled_arm64_objects'] = len(objects)

    result['stage'] = 'pio-relocatable-link'
    result['partial_link_attempts'] = 1
    merged = work / 'note10_iostorage_pio_link.o'
    call = subprocess.run(['xcrun', '--sdk', 'macosx', 'ld', '-r', '-arch', 'arm64',
                           '-o', str(merged), *objects], cwd=ROOT, capture_output=True, timeout=60)
    result['partial_link_returncode'] = call.returncode
    if call.returncode:
        return
    require_arm64_object(merged)
    result['stage'] = 'pio-symbol-audit'
    nm = ['xcrun', '--sdk', 'macosx', 'nm']
    defined = set(read_command([*nm, '-g', '-U', '-j', str(merged)]).splitlines())
    undefined = sorted(set(read_command([*nm, '-u', '-j', str(merged)]).splitlines()))
    require(len(undefined) <= 32 and all(re.fullmatch(r'[A-Za-z_.$][A-Za-z0-9_.$]{0,199}', n)
                                         for n in undefined), 'unexpected undefined symbol output')
    bridge_name = 'note10_iostorage_pio_read'
    bridge_prefix = f'__Z{len(bridge_name)}{bridge_name}'
    bridge = [name for name in defined if name.startswith(bridge_prefix)]
    helpers = {'_note10_iostorage_read_range', '_note10_iostorage_read_request'}
    require(len(bridge) == 1 and helpers <= defined, 'expected bridge and both C helpers')
    require(not any('note10_iostorage_' in name for name in undefined), 'unresolved internal PIO symbol')
    result.update(stage='complete', passed=True, pio_relocatable_link_verified=True,
                  defined_pio_symbols=sorted(helpers | set(bridge)),
                  undefined_external_symbols=undefined, undefined_external_count=len(undefined))


def compile_provider_object(result, work, compiler, includes):
    result['stage'] = 'provider-object-compile'
    obj = work / 'note10_iostorage_provider_probe.o'
    command = [*compiler, *COMPILE_FLAGS[:-1], *includes, '-DN10_RAM_PROVIDER_OBJECT_PROBE=1',
               '-O2', '-c', PROVIDER_SOURCE, '-o', str(obj)]
    result['compile_attempts'] = 1
    call = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
    result['compiler_returncode'] = call.returncode
    if call.returncode:
        return
    require_arm64_object(obj)
    result['compiled_arm64_objects'] = 1
    result['stage'] = 'provider-object-symbol-audit'
    nm = ['xcrun', '--sdk', 'macosx', 'nm']
    defined = set(read_command([*nm, '-g', '-U', '-j', str(obj)]).splitlines())
    undefined = sorted(set(read_command([*nm, '-u', '-j', str(obj)]).splitlines()))
    require(len(undefined) <= 512 and all(re.fullmatch(r'[A-Za-z_.$][A-Za-z0-9_.$]{0,383}', n)
                                          for n in undefined), 'unexpected provider symbol output')
    vtable = f'__ZTV{len(PROVIDER_CLASS)}{PROVIDER_CLASS}'
    require(vtable in defined, 'concrete provider vtable missing')
    require(PROVIDER_BRIDGE_IMPORT in undefined and any('IOBlockStorageDevice' in n for n in undefined)
            and any('OSMetaClass' in n for n in undefined), 'expected provider imports missing')
    result.update(stage='complete', passed=True, provider_object_verified=True,
                  defined_provider_vtable=vtable, undefined_external_symbols=undefined,
                  undefined_external_count=len(undefined))


def compile_base_object(result, source, compiler, includes):
    result['stage'] = 'base-object-compile'
    obj = source.with_suffix('.o')
    command = [*compiler, *COMPILE_FLAGS[:-1], *includes, '-O2', '-c', str(source), '-o', str(obj)]
    result['compile_attempts'] = 1
    call = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
    result['compiler_returncode'] = call.returncode
    if call.returncode:
        match = re.search(rb"fatal error: '([A-Za-z0-9_][A-Za-z0-9_./+\-]{0,127})' file not found", call.stderr)
        if match and b'..' not in match.group(1):
            result['missing_include'] = match.group(1).decode('ascii')
        return
    require_arm64_object(obj)
    result['compiled_arm64_objects'] = 1
    result['stage'] = 'base-object-symbol-audit'
    defined = set(read_command(['xcrun', '--sdk', 'macosx', 'nm', '-g', '-U', '-j', str(obj)]).splitlines())
    result['matched_required_symbols'] = [name for name in BASE_REQUIRED_SYMBOLS if name in defined]
    result['missing_required_symbols'] = [name for name in BASE_REQUIRED_SYMBOLS if name not in defined]
    if not result['missing_required_symbols']:
        result.update(stage='complete', passed=True, base_required_symbols_verified=True)


def public_sdk_context(result, mode):
    result['stage'] = 'sdk-preflight'
    sdk_path = Path(read_command(['xcrun', '--sdk', 'macosx', '--show-sdk-path']))
    require(sdk_path.is_absolute(), 'absolute SDK path required')
    sdk = sdk_path.resolve()
    version = read_command(['xcrun', '--sdk', 'macosx', '--show-sdk-version'])
    require(sdk.is_dir() and re.fullmatch(r'[0-9]+(?:\.[0-9]+){0,2}', version), 'actual macOS SDK required')
    framework = sdk / 'System/Library/Frameworks/Kernel.framework'
    kernel = framework / 'Headers'
    if not kernel.is_dir():
        kernel = framework / 'Versions/A/Headers'
    includes = (kernel, sdk / 'usr/include')
    headers = SDK_HEADERS + BASE_SDK_HEADERS if mode == 'base_object' else SDK_HEADERS
    found = {name: next((directory / name for directory in includes if (directory / name).is_file()), None)
             for name in headers}
    result['sdk_version'] = version
    missing = [name for name, path in found.items() if path is None]
    if not kernel.is_dir() or missing:
        result['missing_sdk_headers'] = missing
        result['public_kernel_headers_available'] = kernel.is_dir()
        return
    result['sdk_header_sha256'] = {name: sha(path.read_bytes()) for name, path in found.items()}
    if mode != 'declaration':
        require(all(result['sdk_header_sha256'][name] == digest for name, digest in PIO_SDK_PINS.items()),
                'reviewed SDK descriptor/type header pin differs')
    if mode in ('provider_object', 'base_object'):
        require(result['sdk_header_sha256']['libkern/c++/OSMetaClass.h'] == PROVIDER_METACLASS_SHA,
                'reviewed SDK metaclass header pin differs')
    return sdk, kernel


def compile_probe(result, mode, source):
    sdk_context = public_sdk_context(result, mode)
    if sdk_context is None:
        return
    sdk, kernel = sdk_context

    with tempfile.TemporaryDirectory(prefix='note10-iostorage-') as work_dir:
        work = Path(work_dir)
        include = work / 'include'
        base_source = work / BASE_MEMBER if mode == 'base_object' else None
        result['stage'] = 'pinned-header-staging'
        result['archive_fetch_attempts'] = 1
        stage_headers(include, base_source)
        result['archive_verified'] = True
        compiler = ['xcrun', '--sdk', 'macosx', 'clang']
        includes = ['-isysroot', str(sdk), '-I', str(include),
                    '-isystem', str(kernel), '-isystem', str(sdk / 'usr/include')]
        if mode == 'pio_link':
            link_pio(result, work, compiler, includes)
            return
        if mode == 'provider_object':
            compile_provider_object(result, work, compiler, includes)
            return
        if base_source is not None:
            result['archive_source_verified'] = True
            compile_base_object(result, base_source, compiler, includes)
            return
        command = [*compiler, *COMPILE_FLAGS, *includes, source]
        result['stage'] = 'pio-bridge-compile' if mode == 'pio_bridge' else 'declaration-compile'
        result['compile_attempts'] = 1
        call = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
        result['compiler_returncode'] = call.returncode
        if call.returncode:
            match = re.search(rb"fatal error: '([A-Za-z0-9_][A-Za-z0-9_./+\-]{0,127})' file not found", call.stderr)
            if match and b'..' not in match.group(1):
                result['missing_include'] = match.group(1).decode('ascii')
            return
        result.update(stage='complete', passed=True)
        if mode == 'pio_bridge':
            result['pio_bridge_syntax_verified'] = True
        else:
            result['declaration_overrides_verified'] = 14


def compile_closure_objects(result, output, *, native_work=None, diagnostic_sink=None):
    sdk_context = public_sdk_context(result, 'base_object')
    if sdk_context is None:
        return
    sdk, kernel = sdk_context
    sdk_json = json.dumps(result['sdk_header_sha256'], sort_keys=True, separators=(',', ':')).encode()
    require(sha(sdk_json) == CLOSURE_PUBLIC_SDK_SHA256, 'accepted public SDK header set differs')

    from phase1_iostorage_native_complete import compile_complete, compile_generated_complete
    public = output / 'public-sdk-objects'
    include = public / 'include'
    base = public / BASE_MEMBER

    @contextmanager
    def stage_shared_archive():
        with open_verified_archive() as archive:
            stage_storage_members(archive, include, base)
            yield archive

    if native_work is None:
        compile_complete(result, output, stage_shared_archive, COMMIT, HEADERS['IOStorage.h'], require_arm64_object)
    else:
        compile_generated_complete(result, output, native_work, stage_shared_archive, COMMIT, HEADERS['IOStorage.h'],
                                   require_arm64_object, existing_exports=True, diagnostic_sink=diagnostic_sink)
    result['unit_compiler_returncodes'] = {}
    if 'compiler_returncode' in result:
        result['unit_compiler_returncodes']['IOStorage.cpp'] = result['compiler_returncode']
    if not result['native_complete_verified']:
        return
    result.update(passed=False, stage='closure-public-object-compile')
    objects = [str(output / 'apple-implementation/IOStorage.o')]
    compiler = ['xcrun', '--sdk', 'macosx', 'clang']
    includes = ['-isysroot', str(sdk), '-I', str(include),
                '-isystem', str(kernel), '-isystem', str(sdk / 'usr/include')]
    units = (
        (str(base), COMPILE_FLAGS[:-1], ()),
        (PROVIDER_SOURCE, COMPILE_FLAGS[:-1], ('-DN10_RAM_PROVIDER_OBJECT_PROBE=1',)),
        (PIO_SOURCE, COMPILE_FLAGS[:-1], ()),
        *((source, C_OBJECT_FLAGS, ()) for source in PIO_LINK_C_SOURCES),
    )
    for source, flags, extra in units:
        obj = public / (Path(source).stem + '.o')
        result['compile_attempts'] += 1
        result['target_object_compile_attempts'] += 1
        try:
            call = subprocess.run([*compiler, *flags, *includes, *extra, '-O2', '-c', source, '-o', str(obj)],
                                  cwd=ROOT, capture_output=True, timeout=60)
        except subprocess.TimeoutExpired as error:
            if diagnostic_sink is not None:
                diagnostic_sink(Path(source).name, None, error.stderr or b'', True)
            raise
        if diagnostic_sink is not None:
            diagnostic_sink(Path(source).name, call.returncode, call.stderr, False)
        result['unit_compiler_returncodes'][Path(source).name] = call.returncode
        if call.returncode:
            return
        require_arm64_object(obj)
        objects.append(str(obj))
        result['compiled_arm64_objects'] = len(objects)
    return objects


def closure_symbols():
    from phase1_iostorage_native_complete import COMPLETE_SYMBOL
    required = (*BASE_REQUIRED_SYMBOLS, PROVIDER_BRIDGE_IMPORT, COMPLETE_SYMBOL,
                '_note10_iostorage_read_range', '_note10_iostorage_read_request')
    return required, f'__ZTV{len(PROVIDER_CLASS)}{PROVIDER_CLASS}'


def compile_relocatable_closure(result, output):
    objects = compile_closure_objects(result, output)
    if objects is None:
        return
    result.update(stage='closure-relocatable-link', partial_link_attempts=1)
    merged = output / 'note10_iostorage_closure.o'
    call = subprocess.run(['xcrun', '--sdk', 'macosx', 'ld', '-r', '-arch', 'arm64',
                           '-o', str(merged), *objects], cwd=ROOT, capture_output=True, timeout=60)
    result['partial_link_returncode'] = call.returncode
    if call.returncode:
        return
    require_arm64_object(merged)

    result['stage'] = 'closure-symbol-audit'
    nm = ['xcrun', '--sdk', 'macosx', 'nm']
    defined = read_command([*nm, '-g', '-U', '-j', str(merged)]).splitlines()
    undefined = sorted(set(read_command([*nm, '-u', '-j', str(merged)]).splitlines()))
    for names in (defined, undefined):
        require(len(names) <= 512 and all(re.fullmatch(r'[A-Za-z_.$][A-Za-z0-9_.$]{0,383}', n)
                                         for n in names), 'unexpected relocatable symbol output')
    required, provider_vtable = closure_symbols()
    require(all(defined.count(name) == 1 for name in (*required, provider_vtable)),
            'missing or duplicate closure definition')
    require(not any(name in required or 'note10_iostorage_' in name or PROVIDER_CLASS in name or
                    'IOBlockStorageDevice' in name for name in undefined), 'unresolved internal storage symbol')
    result.update(stage='complete', passed=True, relocatable_closure_verified=True,
                  resolved_by_composition=sorted(required), defined_provider_vtable=provider_vtable,
                  defined_external_symbols=sorted(defined), defined_external_count=len(defined),
                  undefined_external_symbols=undefined, undefined_external_count=len(undefined))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('declaration', 'pio_bridge', 'pio_link', 'provider_object', 'base_object',
                                          'native_inputs', 'native_complete', 'relocatable_closure',
                                          'user_instruction_object', 'user_instruction_diagnostics',
                                          'user_instruction_header_context', 'user_auth_branch_object',
                                          'user_auth_branch_closure', 'memdev_wide_extent',
                                          'memdev_context_observation'),
                        default='declaration')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    head, run_id = reviewed_identity()
    out = (ROOT / args.output).resolve()
    private = ROOT / 'note10/private'
    require(out != private and out.is_relative_to(private), 'fresh private result directory required')
    out.mkdir(parents=True)
    pio = args.mode in ('pio_bridge', 'pio_link')
    provider = args.mode == 'provider_object'
    base = args.mode == 'base_object'
    native_inputs = args.mode == 'native_inputs'
    native_complete = args.mode == 'native_complete'
    closure = args.mode == 'relocatable_closure'
    auth_branch = args.mode == 'user_auth_branch_object'
    user_branch_closure = args.mode == 'user_auth_branch_closure'
    memdev_context = args.mode == 'memdev_context_observation'
    memdev_wide = args.mode in ('memdev_wide_extent', 'memdev_context_observation')
    header_context = args.mode in ('user_instruction_header_context', 'user_auth_branch_object')
    diagnostics = args.mode in ('user_instruction_diagnostics', 'user_instruction_header_context', 'user_auth_branch_object')
    user_fetch = args.mode in ('user_instruction_object', 'user_instruction_diagnostics',
                              'user_instruction_header_context', 'user_auth_branch_object')
    source = {
        'declaration': SOURCE, 'pio_bridge': PIO_SOURCE, 'pio_link': PIO_SOURCE,
        'provider_object': PROVIDER_SOURCE, 'native_inputs': NATIVE_INPUTS_SOURCE,
        'native_complete': NATIVE_COMPLETE_SOURCE,
        'user_instruction_object': USER_FETCH_SOURCE,
        'user_instruction_diagnostics': USER_FETCH_SOURCE,
        'user_instruction_header_context': USER_FETCH_SOURCE,
        'user_auth_branch_object': USER_FETCH_SOURCE,
        'user_auth_branch_closure': USER_BRANCH_CLOSURE_SOURCE,
        'memdev_wide_extent': MEMDEV_WIDE_SOURCE,
        'memdev_context_observation': MEMDEV_WIDE_SOURCE,
    }.get(args.mode)
    paths = (WORKFLOW, Path(__file__).resolve().relative_to(ROOT).as_posix())
    if source is not None:
        paths += (source,)
    if pio:
        paths += PIO_INPUTS
    if args.mode == 'pio_link':
        paths += PIO_LINK_C_SOURCES
    if provider:
        paths += (PIO_INPUTS[0],)
    if native_complete:
        paths += (NATIVE_INPUTS_SOURCE,)
    if closure:
        paths += (NATIVE_INPUTS_SOURCE, *CLOSURE_INPUT_SHA256)
    schema = f'note10-phase1-iostorage-{args.mode.replace("_", "-")}-result-v1'
    result = dict(schema=schema, passed=False,
                  source_head=head, run_id=run_id, run_attempt=1, target=TARGET,
                  source_sha256={name: sha((ROOT / name).read_bytes()) for name in paths},
                  iostorage_commit=COMMIT, archive_sha256=ARCHIVE_SHA, archive_header_sha256=HEADERS,
                  archive_fetch_attempts=0, compile_attempts=0, kernel_builds=0, old_tests_count=0,
                  device_operations=0, deployment_ready=False)
    if user_fetch:
        result['schema'] = ('note10-v165-user-auth-branch-object-result-v1' if auth_branch else
                            'note10-v164-user-instruction-header-context-result-v1' if header_context else
                            'note10-v163-user-instruction-diagnostics-result-v1' if diagnostics else
                            'note10-v162-user-instruction-object-result-v1')
        for name in ('iostorage_commit', 'archive_sha256', 'archive_header_sha256'):
            del result[name]
    if user_branch_closure:
        result['schema'] = 'note10-v166-user-auth-branch-closure-result-v1'
        for name in ('iostorage_commit', 'archive_sha256', 'archive_header_sha256'):
            del result[name]
    if memdev_wide:
        result['schema'] = ('note10-v169-memdev-context-observation-result-v1' if memdev_context else
                            'note10-v168-memdev-wide-extent-result-v1')
        for name in ('iostorage_commit', 'archive_sha256', 'archive_header_sha256'):
            del result[name]
    if args.mode == 'pio_link':
        result.update(compiled_arm64_objects=0, partial_link_attempts=0, pio_relocatable_link_verified=False)
    if provider:
        result.update(compiled_arm64_objects=0, partial_link_attempts=0, provider_object_verified=False)
    if base:
        result.update(compiled_arm64_objects=0, partial_link_attempts=0, base_required_symbols_verified=False,
                      archive_source_member='IOStorageFamily-' + COMMIT + '/' + BASE_MEMBER,
                      archive_source_sha256=BASE_MEMBER_SHA, archive_source_bytes=BASE_MEMBER_BYTES,
                      archive_source_verified=False, required_symbol_count=len(BASE_REQUIRED_SYMBOLS))
    try:
        if memdev_wide:
            from phase1_memdev_wide_extent import compile_memdev
            compile_memdev(result, out, require_arm64_object, context_observation=memdev_context)
        elif user_branch_closure:
            from phase1_user_auth_branch_closure import compile_auth_branch_closure
            compile_auth_branch_closure(result, out, require_arm64_object)
        elif user_fetch:
            from phase1_user_instruction_fetch import compile_object
            if auth_branch:
                compile_object(result, out, require_arm64_object, diagnostics=True, header_context=True,
                               auth_branch=True)
            elif diagnostics:
                compile_object(result, out, require_arm64_object, diagnostics=True, header_context=header_context)
            else:
                compile_object(result, out, require_arm64_object)
        elif native_inputs or native_complete or closure:
            result.update(native_inputs_generated=False, host_config_tool_built=False,
                          target_object_compile_attempts=0)
            if native_complete or closure:
                require(result['source_sha256'][NATIVE_INPUTS_SOURCE] == NATIVE_INPUTS_SHA256,
                        'accepted native generation source differs')
                from phase1_iostorage_native_complete import compile_complete, MEMBER, MEMBER_BYTES, MEMBER_SHA256
                result.update(native_complete_verified=False, compiled_arm64_objects=0, partial_link_attempts=0,
                              archive_source_verified=False, archive_source_member='IOStorageFamily-' + COMMIT + '/' + MEMBER,
                              archive_source_bytes=MEMBER_BYTES, archive_source_sha256=MEMBER_SHA256)
                if closure:
                    require(all(result['source_sha256'][name] == digest for name, digest in
                                CLOSURE_INPUT_SHA256.items()), 'accepted composition input source differs')
                    result.update(relocatable_closure_verified=False,
                                  archive_base_source_member='IOStorageFamily-' + COMMIT + '/' + BASE_MEMBER,
                                  archive_base_source_bytes=BASE_MEMBER_BYTES, archive_base_source_sha256=BASE_MEMBER_SHA)
                    compile_relocatable_closure(result, out)
                else:
                    compile_complete(result, out, open_verified_archive, COMMIT, HEADERS['IOStorage.h'],
                                     require_arm64_object)
            else:
                from phase1_iostorage_native_inputs import generate
                generate(result, out)
        else:
            compile_probe(result, args.mode, source)
    except Exception as error:
        result.update(passed=False, failure_type=type(error).__name__)
    if user_fetch:
        if 'fresh_generated_headers' in result:
            result['generated_header_sha256'] = sorted(
                item['sha256'] for item in result['fresh_generated_headers'].values())
        public_fields = '''schema passed source_head run_id run_attempt target scope stage failure_type
            source_sha256 host_pass compiler_version sdk_version fresh_tool_sha256 generated_header_sha256
            native_inputs_generated host_config_tool_built public_reference_sha256 native_reference_sha256
            public_xnu_commit osfmk_config_defines_sha256 osfmk_config_header_sha256
            osfmk_generated_headers_sha256 osfmk_makefile_sha256 compiler_flags compiler_argv_count
            compiler_argv_sha256 compile_attempts target_object_compile_attempts compiled_arm64_objects
            compiler_returncode missing_include_sha256 object_sha256 object_bytes defined_external_symbols
            undefined_external_symbols user_instruction_object_verified partial_link_attempts kernel_builds
            kernel_links old_tests_count device_operations deployment_ready production_hook
            firmware_abi_verified synthetic_board_inputs exact_target_source'''.split()
        if diagnostics:
            public_fields.append('compiler_diagnostics')
        if header_context:
            public_fields.append('header_context')
        if auth_branch:
            public_fields.remove('user_instruction_object_verified')
            public_fields.extend(('user_auth_branch_object_verified', 'composition_host_pass',
                                  'carried_fetch_native_result_sha256'))
        result = {name: result[name] for name in public_fields if name in result}
    elif user_branch_closure:
        public_fields = '''schema passed source_head run_id run_attempt target source_sha256 scope stage failure_type
            compile_attempts target_object_compile_attempts compiled_arm64_objects partial_link_attempts
            partial_link_returncode closure_verified defined_external_symbols undefined_external_symbols
            merged_object_sha256 merged_object_bytes old_tests_count kernel_builds kernel_links device_operations
            deployment_ready production_hook firmware_abi_verified synthetic_board_inputs exact_target_source
            fresh_tool_sha256 compiler_version sdk_version native_inputs_generated host_config_tool_built
            generated_header_sha256 public_reference_sha256 native_reference_sha256 public_xnu_commit
            osfmk_config_defines_sha256 osfmk_config_header_sha256 osfmk_generated_headers_sha256 osfmk_makefile_sha256
            header_context decoder_source units link carried_evidence'''.split()
        result = {name: result[name] for name in public_fields if name in result}
    elif memdev_wide:
        public_fields = '''schema passed source_head run_id run_attempt target source_sha256 scope stage failure_type
            host_pass compile_attempts target_object_compile_attempts compiled_arm64_objects partial_link_attempts
            kernel_builds kernel_links old_tests_count device_operations deployment_ready production_hook
            firmware_abi_verified synthetic_board_inputs exact_target_source compiler_version sdk_version
            fresh_tool_sha256 generated_header_sha256 native_inputs_generated host_config_tool_built
            public_xnu_commit public_reference_sha256 bsd_makefile_sha256 bsd_generated_headers_sha256
            bsd_config_header_sha256 bsd_config_defines_sha256 kernel_support_header_sha256 memdev_source
            compiler_flags compiler_argv_count compiler_argv_sha256 compiler_returncode compiler_timed_out
            compiler_diagnostics object_sha256 object_bytes defined_external_symbols undefined_external_symbols
            memdev_object_verified'''.split()
        if memdev_context:
            public_fields.extend(('context_observation', 'config_projection'))
        result = {name: result[name] for name in public_fields if name in result}
    raw = json.dumps(result, indent=2, sort_keys=True) + '\n'
    (out / 'result.json').write_text(raw, encoding='utf-8', newline='\n')
    print(raw, end='')
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
