"""Check one public IOStorage C++ source against the actual macOS SDK."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'note10/xnu26/phase1_iostorage_declaration.cpp'
PIO_SOURCE = 'note10/xnu26/note10_iostorage_pio_bridge.cpp'
PIO_INPUTS = (
    'note10/xnu26/note10_iostorage_pio_bridge.h',
    'note10/xnu26/note10_iostorage_read_request.h',
    'note10/xnu26/note10_iostorage_read_range.h',
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
TARGET = 'arm64-apple-ios26.5.2'
COMPILE_FLAGS = (
    '--target=' + TARGET, '-std=gnu++2b', '-mkernel', '-fapple-kext', '-fsized-deallocation',
    '-ffreestanding', '-fno-builtin', '-fno-common', '-fblocks', '-nostdlibinc', '-nostdinc++',
    '-DKERNEL=1', '-ferror-limit=8', '-fsyntax-only',
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


def stage_headers(include):
    with urllib.request.urlopen(ARCHIVE_URL, timeout=30) as response:
        raw = response.read(ARCHIVE_BYTES + 1)
    require(len(raw) == ARCHIVE_BYTES and sha(raw) == ARCHIVE_SHA, 'public IOStorageFamily archive pin differs')
    storage = include / 'IOKit/storage'
    storage.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        for name, digest in HEADERS.items():
            member = archive.getmember('IOStorageFamily-' + COMMIT + '/' + name)
            require(member.isfile() and 0 < member.size <= 1024 * 1024, 'expected ordinary bounded archive header')
            with archive.extractfile(member) as stream:
                data = stream.read()
            require(sha(data) == digest, 'public IOStorageFamily header pin differs')
            (storage / name).write_bytes(data)


def compile_probe(result, mode, source):
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
    found = {name: next((directory / name for directory in includes if (directory / name).is_file()), None)
             for name in SDK_HEADERS}
    result['sdk_version'] = version
    missing = [name for name, path in found.items() if path is None]
    if not kernel.is_dir() or missing:
        result['missing_sdk_headers'] = missing
        result['public_kernel_headers_available'] = kernel.is_dir()
        return
    result['sdk_header_sha256'] = {name: sha(path.read_bytes()) for name, path in found.items()}
    if mode == 'pio_bridge':
        require(all(result['sdk_header_sha256'][name] == digest for name, digest in PIO_SDK_PINS.items()),
                'reviewed SDK descriptor/type header pin differs')

    with tempfile.TemporaryDirectory(prefix='note10-iostorage-') as work:
        include = Path(work) / 'include'
        result['stage'] = 'pinned-header-staging'
        result['archive_fetch_attempts'] = 1
        stage_headers(include)
        result['archive_verified'] = True
        command = ['xcrun', '--sdk', 'macosx', 'clang', *COMPILE_FLAGS, '-isysroot', str(sdk), '-I', str(include),
                   '-isystem', str(kernel), '-isystem', str(sdk / 'usr/include'), source]
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('declaration', 'pio_bridge'), default='declaration')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    head, run_id = reviewed_identity()
    out = (ROOT / args.output).resolve()
    private = ROOT / 'note10/private'
    require(out != private and out.is_relative_to(private), 'fresh private result directory required')
    out.mkdir(parents=True)
    pio = args.mode == 'pio_bridge'
    source = PIO_SOURCE if pio else SOURCE
    paths = (source, WORKFLOW, Path(__file__).resolve().relative_to(ROOT).as_posix())
    if pio:
        paths += PIO_INPUTS
    schema = 'note10-phase1-iostorage-pio-bridge-result-v1' if pio else 'note10-phase1-iostorage-declaration-result-v1'
    result = dict(schema=schema, passed=False,
                  source_head=head, run_id=run_id, run_attempt=1, target=TARGET,
                  source_sha256={name: sha((ROOT / name).read_bytes()) for name in paths},
                  iostorage_commit=COMMIT, archive_sha256=ARCHIVE_SHA, archive_header_sha256=HEADERS,
                  archive_fetch_attempts=0, compile_attempts=0, kernel_builds=0, old_tests_count=0,
                  device_operations=0, deployment_ready=False)
    try:
        compile_probe(result, args.mode, source)
    except Exception as error:
        result.update(passed=False, failure_type=type(error).__name__)
    raw = json.dumps(result, indent=2, sort_keys=True) + '\n'
    (out / 'result.json').write_text(raw, encoding='utf-8', newline='\n')
    print(raw, end='')
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
