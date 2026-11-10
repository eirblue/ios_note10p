"""Compile only unmodified Apple IOStorage.cpp in the native IOKit context."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from phase1_iostorage_native_inputs import ROOT, command, fresh_headers, generate, require, sha


MEMBER = 'IOStorage.cpp'
MEMBER_BYTES = 11675
MEMBER_SHA256 = '26dc9ccabccb23a24862b4ce0b4ab6cbe73319743df10fa17f8fb5a0b1943966'
COMPLETE_SYMBOL = '__ZN9IOStorage8completeEP19IOStorageCompletioniy'
CONFIG_DEFINES_SHA256 = '39fdf9bb9b9f9b724485bff2ac4d9f5fe8a238d9e56e5728f20f52c43e670a60'
CORE_ENTITLEMENTS_SHA256 = 'e786a99b0221e67e501ad0229596b80ff6bb6fc95a7c9c23f092750bbcd28658'
GENERATION_TOOL_SHA256 = {
    'clang': 'd2e4bf622758eee1bf7267c060497fb2c41e098d37b0fca8be73898dc7e14eda',
    'iig': '308a5dd31cf4b1293bc93897040c22aba874834ddd2cd1d5e25a4a2d90b077a1',
    'mig': '72210518ef314ef0517869283f6fe1cf990844eefaa15e76c007f9b97d4abcdd',
    'unifdef': 'bead4cb98b7c490960747cf35f6f455068d205f67757c5ea10424384eab3a5f1',
}
GENERATION_HEADER_SHA256 = {
    'configured/DEVELOPMENT/iokit/meta_features.h': 'd157200a4e0481e11d6b148a049da72ade3206a14c6b77e0c69661c78f2c00b8',
    'generated-extra/iokit/DriverKit/IOMemoryDescriptor.h': '185fb4ce12ab0d370061c5dc0bf8fed1700af2daf423f2ea7ba59ab643e6bf56',
    'generated-extra/iokit/DriverKit/IOMemoryMap.h': '6ef8f7b33cf4b4bbfd1021fbad2ea7c73bec53ed80109074ce98a076f6a299a6',
    'generated-extra/iokit/DriverKit/IOService.h': '4b779d160b3c59abdc1cd731303478c296d03b07c740fdb264e5cd6826b4e3f7',
    'generated-extra/iokit/DriverKit/OSObject.h': 'f7a089df798052ebde3f2372e6ac39806042329c6b771d629a98988280af4d1c',
    'native-link/include/libkern/version.h': 'f4b7a1018b310ab7ec90ba303355ec28c2f4010d3c488e133bbc949c4c645046',
    'native-mig/export/osfmk/mach/mach_host.h': 'b4f21a75f56e022ba54fe2b965ac453df9b88584bea14cae9aa32d054d9824dd',
}
EXPORTS_SHA256 = {
    'osfmk/libsa/string.h': '630b7c4668cd1ed1995fd6b3fc4a1e1f33d592f1bb100f4c6a00e58a819fb514',
    'san/coverage/kcov.h': '9acc245153ffe0ece6cd2b0e8b967fd04f1cf9597a9a969835c70f900f65bada',
    'san/coverage/kcov_data.h': '57593d14f7f72279aee83e8d689b5dd910ebcb48898179c9bab44113f88fb200',
    'san/coverage/kcov_ksancov.h': '4eddfc35f3b8e732157ccece0a5c8d549733be4ecb559199d32993e74d90d12b',
    'san/coverage/kcov_ksancov_data.h': 'cfeca5cced1455d79ca03357ac9ea58ec834423892199488b5a88607a442c756',
    'san/coverage/kcov_stksz.h': 'f432c06271fcb0346a8f075c0f4d4e9fd90e095ff6a32559e0f63c8388007e94',
    'san/coverage/kcov_stksz_data.h': '0b9e6bc6c184d98a34d77b49d144b2cb8490461853ffca21c9a085a2cf6db516',
    'san/memory/kasan.h': 'c325dae4a4f8c99dbe7bb08eddd0683eb7c146e6dc47c524b0dd3707c300c3f9',
    'san/memory/kasan-classic.h': '3d9256df02fb08c1d31a828ca4545866138f74084b96fad53b48317a3ff0b3ff',
    'san/memory/kasan-tbi.h': '9dbc7cd2cc177f2859336aba1bf3b5eb38dc3bacba173faa1be7c226bf2781f5',
    'san/memory/ubsan_minimal.h': '4c8d9d9a9c89ca037b0b08412c0637e054e5a2900930626069c9348fd1857114',
    'san/memory/memintrinsics.h': '985fccdd08b78522cf15159e031061e4678941ee22d83c1ba010f0e624a7b0eb',
}
PRE_CONFIG_FLAGS = (
    '--target=arm64-apple-ios26.5.2', '-march=armv8.2-a+crypto', '-mcpu=generic', '-std=gnu++2b',
    '-O2', '-ffreestanding', '-fno-builtin', '-fno-common', '-fblocks', '-nostdlibinc',
    '-fno-stack-protector', '-mno-implicit-float', '-mstrict-align', '-ferror-limit=8',
    '-Darm64', '-DARM64', '-D__ARM64__', '-DLP64', '-DAPPLE', '-DKERNEL', '-DKERNEL_PRIVATE',
    '-DXNU_KERNEL_PRIVATE', '-DPRIVATE', '-D__API__=v4', '-DPAGE_SIZE_FIXED', '-DARM_LARGE_MEMORY=0',
    '-DVM_KERNEL_LINK_ADDRESS=0xfffffff007004000', '-DCURRENT_MACHINE_CONFIG_LC=exynos9825',
    '-DXNU_TARGET_OS_IOS', '-DXNU_PLATFORM_iPhoneOS', '-DARM64_BOARD_CONFIG_EXYNOS9825',
    '-DN10_BOARD_SCHEMA=1', '-DN10_ICACHE_LINE_LOG2=6', '-DN10_DCACHE_LINE_LOG2=6',
    '-DN10_MAX_CACHE_LINE_LOG2=7', '-DN10_KERNEL_PAGE_SHIFT=14',
)
POST_CONFIG_FLAGS = (
    '-mkernel', '-fno-c++-static-destructors', '-ftrivial-auto-var-init=zero', '-fsigned-bitfields',
    '-fmerge-all-constants', '-fno-strict-aliasing', '-momit-leaf-frame-pointer',
    '-fno-branch-target-identification', '-mno-implicit-sme', '-fapple-kext', '-fsized-deallocation',
    '-nostdinc++', '-DDRIVER_PRIVATE', '-DIOKIT_KERNEL_PRIVATE', '-DDRIVERKIT_PRIVATE=1',
    '-DIOMATCHDEBUG=1', '-DIOALLOCDEBUG=1', '-DPRIVATE_WIFI_ONLY=1', '-DIOASSERT=1',
    '-DIMAGE4_STRIP_AVAILABILITY=1',
)


def write_pinned(data, destination, digest):
    require(hashlib.sha256(data).hexdigest() == digest, 'native declaration or Apple member pin differs')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(data)


def stage_exports(source, native, *, existing=False):
    def bind(original, destination, digest):
        if existing:
            require(not destination.is_symlink() and sha(destination) == digest,
                    'current native declaration export differs')
        else:
            write_pinned(original.read_bytes(), destination, digest)

    for relative, digest in EXPORTS_SHA256.items():
        path = Path(relative)
        exported = Path('san') / path.name if relative.startswith('san/') else Path(path.name)
        bind(source / path, native / 'exports' / exported, digest)
    entitlement = Path('CoreEntitlements/V2/Kernel.h')
    support = ROOT / 'host-tools/kdk/headers/KDK.pkg/System/Library/KernelSupport'
    bind(support / entitlement, native / 'kernel-support-declarations' / entitlement, CORE_ENTITLEMENTS_SHA256)


def stage_apple(archive, stage, commit, header_sha):
    members = (
        (MEMBER, MEMBER_BYTES, MEMBER_SHA256, stage / MEMBER),
        ('IOStorage.h', 28158, header_sha, stage / 'include/IOKit/storage/IOStorage.h'),
    )
    for name, size, digest, destination in members:
        member = archive.getmember(f'IOStorageFamily-{commit}/{name}')
        require(member.isfile() and member.size == size, 'Apple storage member size differs')
        with archive.extractfile(member) as stream:
            write_pinned(stream.read(), destination, digest)


def include_paths(apple, native, source, sdk):
    yield from (apple / 'include', native / 'native-link/include', native / 'configured/DEVELOPMENT/iokit',
                native / 'exports', source / 'EXTERNAL_HEADERS', native / 'generated-extra/iokit',
                native / 'generated-extra/bsd', native / 'generated-extra/iokit',
                native / 'native-mig/export/osfmk')
    for component in ('iokit', 'osfmk', 'bsd', 'pexpert', 'libkern', 'libsa', 'security', 'san', 'EXTERNAL_HEADERS'):
        yield native / 'source-exports' / component
    for component in ('osfmk', 'bsd', 'libkern', 'pexpert', 'libsa', 'security', 'san'):
        yield native / 'configured/DEVELOPMENT' / component
    for component in ('osfmk', 'bsd', 'pexpert', 'libkern', 'libsa', 'iokit', 'security', 'san', '.'):
        yield source / component
    kdk = ROOT / 'host-tools/kdk/headers/KDK_SDK.pkg/System/Library/Frameworks/Kernel.framework'
    yield from (kdk / 'Versions/A/PrivateHeaders/platform', native / 'kernel-support-declarations',
                ROOT / 'host-tools/opensource-declarations')
    framework = sdk / 'System/Library/Frameworks/Kernel.framework'
    yield from (framework / 'Versions/A/Headers', framework / 'Versions/A/PrivateHeaders',
                framework / 'Headers', framework / 'PrivateHeaders', sdk / 'usr/local/include', sdk / 'usr/include')


def compile_complete(result, output, open_archive, commit, header_sha, require_arm64_object):
    generate(result, output)
    compile_generated_complete(result, output, output / 'native-work', open_archive, commit, header_sha,
                               require_arm64_object)


def compile_generated_complete(result, output, work, open_archive, commit, header_sha, require_arm64_object,
                               *, existing_exports=False, diagnostic_sink=None):
    result.update(passed=False, stage='native-complete-input-binding')
    require(result['fresh_tool_sha256'] == GENERATION_TOOL_SHA256 and
            {name: item['sha256'] for name, item in result['fresh_generated_headers'].items()} ==
            GENERATION_HEADER_SHA256, 'fresh native inputs differ from accepted generation')
    native = ROOT / 'note10/private/windows-xnu'
    context = json.loads((work / 'context.json').read_bytes())
    source = work / 'source'
    compiler = command('xcrun', '-f', 'clang')
    sdk = Path(command('xcrun', '--sdk', 'macosx', '--show-sdk-path'))
    require(context['source'] == str(source) and context['compiler'] == compiler and context['sdk'] == str(sdk) and
            context['ci_context']['GITHUB_SHA'] == result['source_head'] and
            context['ci_context']['GITHUB_RUN_ID'] == str(result['run_id']) and
            context['ci_context']['GITHUB_RUN_ATTEMPT'] == '1', 'same-run native context required')

    from build_native_bootstrap_selection import definitions
    config = native / 'configured/DEVELOPMENT/iokit'
    flags = definitions((config / 'Makefile').read_text())
    require(hashlib.sha256(json.dumps(flags, separators=(',', ':')).encode()).hexdigest() ==
            CONFIG_DEFINES_SHA256, 'native IOKit config defines differ')
    stage_exports(source, native, existing=existing_exports)
    apple = output / 'apple-implementation'
    result['archive_fetch_attempts'] = 1
    with open_archive() as archive:
        stage_apple(archive, apple, commit, header_sha)
    result.update(archive_verified=True, archive_source_verified=True)
    require(fresh_headers(native) == result['fresh_generated_headers'], 'same-run generated headers changed')
    tools = {name: sha(Path(command('xcrun', '-f', name))) for name in ('clang', 'iig', 'mig', 'unifdef')}
    require(tools == result['fresh_tool_sha256'], 'same-run native tools changed')
    result['fresh_inputs_reverified'] = True

    obj = apple / 'IOStorage.o'
    argv = [compiler, *PRE_CONFIG_FLAGS, '-include', str(config / 'meta_features.h'), *flags,
            '-isysroot', str(sdk), *POST_CONFIG_FLAGS]
    for path in include_paths(apple, native, source, sdk):
        argv.extend(('-I', str(path)))
    argv.extend(('-c', str(apple / MEMBER), '-o', str(obj)))
    result.update(stage='native-complete-compile', compile_attempts=1, target_object_compile_attempts=1)
    try:
        call = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired as error:
        if diagnostic_sink is not None:
            diagnostic_sink(MEMBER, None, error.stderr or b'', True)
        raise
    if diagnostic_sink is not None:
        diagnostic_sink(MEMBER, call.returncode, call.stderr, False)
    result['compiler_returncode'] = call.returncode
    if call.returncode:
        match = re.search(rb"fatal error: '([A-Za-z0-9_][A-Za-z0-9_./+\-]{0,127})' file not found", call.stderr)
        if match and b'..' not in match.group(1):
            result['missing_include'] = match.group(1).decode('ascii')
        elif b'incomplete type' in call.stderr:
            result['compiler_failure_kind'] = 'incomplete-type'
        return
    require_arm64_object(obj)
    result.update(stage='native-complete-symbol-audit', compiled_arm64_objects=1)
    symbols = command('xcrun', '--sdk', 'macosx', 'nm', '-g', '-U', '-j', str(obj)).splitlines()
    require(symbols.count(COMPLETE_SYMBOL) == 1, 'exact external completion definition required')
    result.update(stage='complete', passed=True, native_complete_verified=True,
                  defined_completion_symbol=COMPLETE_SYMBOL)
