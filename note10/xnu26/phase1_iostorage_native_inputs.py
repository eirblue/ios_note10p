"""Generate the retained native IOKit header inputs without compiling kernel units."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[2]
RECIPE_SHA256 = {
    'xnu26/build_native_bootstrap_selection.py': '3cb6f5e2a6d88887597e44a24a5b60e1beeef494cf3b6010b3dea6912d9f5513',
    'xnu26/cloud_compile.py': 'd449300ee75d09b56452ad19f85d580c80f99be3239c0981ab27ccc3559e1980',
    'xnu26/export_source_headers.py': '671d813c5408ebedfe1ad151e1585bbb3dd5c889a021aafc7e0908e98f618ce9',
    'xnu26/generate_link_metadata.py': '5c3117444622fec86fcf17d2677e15486ff2d0c21822cc5b2c047effc5f0034a',
    'xnu26/generate_native_extra.py': '1f5e4e41cdafbb686ef05f6831ad92c365a9bf7a0534d477fc144f7bd51d9acd',
    'xnu26/generate_native_mig.py': 'e99f8d4156459a6ba3d49de02ab4b849a2a00ce5cdff08bcb3dd0280549d1256',
    'xnu26/prepare_native_bootstrap_selection.py': 'ea5f56c05f87bbe887c0b27805cdba32791fe83f477ce56d6fe7a0688a5d5a9a',
    'xnu26/prepare_build_selection.py': '586a8e53050cb890d7a478c559111856b752b04ed43a58066d412a9fa691be1c',
    'xnu26/prepare_exynos_early_clock.py': '17b903a562c1c4e8355b351902042740091ae409a11b24e04f5532d819191325',
    'xnu26/prepare_exynos_leaf_mapper.py': 'b1c76637d999d6c6821e7fd5910783080eabfe192094a624760dae1e02a9ac12',
    'xnu26/prepare_exynos_checked_ptpage.py': 'a67781fb67b14d95d8a3fd64c99c35ddd5b1753db3759be9e16f12b292d7ae4b',
    'extract_kdk_headers.py': 'da8d53409c23ad8a4fb3510c10eeae5cbdbb69d7e7982def9fcd61d42cee29f5',
}
PATCH_MANIFEST_SHA256 = '23d614bdf2a12ebaaea8c6045888b6456c7977ef78b1eee71253dacac34c7542'
XNU_COMMIT = 'ac9718fb1af618d5ce8678d0dc6e8a58f252216f'
KDK_SHA256 = '90ed319cd1ba6e23d1eefcee89fa1b10743f4cf60b85208ae52aa9f45543c7aa'
FIREHOSE_SHA256 = 'b1da2269d930974d1fb122d90446534553829dc2a3b090b3d0ea0813fd95dd45'
FIREHOSE_URL = ('https://raw.githubusercontent.com/apple-oss-distributions/libdispatch/'
                '2361ffb78a76f7ee488cd052eb0bc5c767118bf9/os/firehose_buffer_private.h')
CLANG_VERSION = 'Apple clang version 21.0.0 (clang-2100.1.1.101)'
SDK_VERSION = '26.5'
IIG_DEFINITIONS = {
    'IOMemoryDescriptor': '45df15591122b1f8cae88b974fe5fb8240213a6d3c6a56e0af85d9d5b85a86ba',
    'IOMemoryMap': '335655b5e7d7b160cc9be9494279911a89ce73f9d35257381815caddad98a6fc',
    'IOService': '874c48d99a6663f339a21479d05fd39d2fdca0f6fdf0c1515d8d71391826363a',
    'OSObject': 'bcd00a8dfda6bbb511156ca23cb9a6b1685a828c6b91bb589144bba91215aca1',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def command(*argv):
    return subprocess.check_output(argv, cwd=ROOT, stderr=subprocess.DEVNULL,
                                   timeout=30, text=True).strip()


def verify_retained_inputs():
    require(all(sha(ROOT / 'note10' / name) == digest for name, digest in RECIPE_SHA256.items()),
            'retained native recipe differs')
    patches = ROOT / 'note10/xnu26/patches'
    series = (patches / 'series').read_text().splitlines()
    require(len(series) == 13 and len(set(series)) == 13 and
            all(re.fullmatch(r'\d{4}-[a-z0-9-]+\.patch', name) for name in series),
            'expected reviewed native patch series')
    manifest = {name: sha(patches / name) for name in series}
    raw = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()
    require(hashlib.sha256(raw).hexdigest() == PATCH_MANIFEST_SHA256 and
            list(manifest) == sorted(manifest), 'native patch inputs differ')


def fresh_headers(native):
    extra = json.loads((native / 'native-extra-result.json').read_bytes())
    mig = json.loads((native / 'native-mig-result.json').read_bytes())
    require(extra['iig_available'] and mig['all_passed'], 'native IIG and MIG generation required')
    selected = {row['selected_name']: row for row in extra['generated_sources'] if row['passed']}
    for name, digest in IIG_DEFINITIONS.items():
        row = selected.get(f'./DriverKit/{name}.iig.cpp')
        require(row is not None and row['definition_sha256'] == digest, 'required IIG generation differs')
    paths = [f'generated-extra/iokit/DriverKit/{name}.h' for name in IIG_DEFINITIONS]
    paths += ['native-mig/export/osfmk/mach/mach_host.h', 'native-link/include/libkern/version.h',
              'configured/DEVELOPMENT/iokit/meta_features.h']
    metadata = {}
    for name in paths:
        path = native / name
        require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 1024 * 1024,
                'required generated header absent or invalid')
        metadata[name] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
    return metadata


def generate(result, output):
    # The SDK mode dispatch checks the exact head and first attempt before entry.
    result['stage'] = 'native-input-preflight'
    verify_retained_inputs()
    native = ROOT / 'note10/private/windows-xnu'
    require(not native.exists() and not native.is_symlink(), 'fresh native generated root required')
    compiler = command('xcrun', '-f', 'clang')
    sdk = command('xcrun', '--sdk', 'macosx', '--show-sdk-path')
    version = command(compiler, '--version').splitlines()[0]
    require(version == CLANG_VERSION and Path(sdk).name == 'MacOSX26.5.sdk' and
            command('xcrun', '--sdk', 'macosx', '--show-sdk-version') == SDK_VERSION,
            'reviewed Apple toolchain required')
    make = shutil.which('make')
    require(make and shutil.which('bison') and shutil.which('flex'), 'native config tools required')
    result.update(compiler_version=version, sdk_version=SDK_VERSION,
                  fresh_tool_sha256={name: sha(Path(command('xcrun', '-f', name)))
                                     for name in ('clang', 'iig', 'mig', 'unifdef')})

    import build_native_bootstrap_selection as bootstrap
    import cloud_compile
    import export_source_headers
    import generate_link_metadata
    import generate_native_extra
    import generate_native_mig

    require(bootstrap.COMMIT == XNU_COMMIT and cloud_compile.KDK_SHA == KDK_SHA256,
            'retained XNU and KDK pins differ')
    result['stage'] = 'native-provisioning'
    ci = {name: os.environ[name] for name in ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT',
          'GITHUB_JOB', 'GITHUB_WORKFLOW_REF', 'GITHUB_WORKFLOW_SHA', 'GITHUB_REPOSITORY')}
    work = output / 'native-work'
    bootstrap.provision(work, output / 'native-provisioning', ci=ci, leaf=True, checked=True)
    context = json.loads((work / 'context.json').read_bytes())
    require(context['compiler'] == compiler and context['sdk'] == sdk and
            context['public_source_commit'] == XNU_COMMIT, 'provisioned native context differs')
    result['host_config_tool_built'] = True
    source = Path(context['source'])
    require(all(sha(source / f'iokit/DriverKit/{name}.iig') == digest
                for name, digest in IIG_DEFINITIONS.items()), 'retained IIG input differs')
    os.environ.update(N10_CC=compiler, N10_SDKROOT=sdk, N10_MAKE=make)

    result['stage'] = 'native-configuration'
    native.mkdir()
    configured = []
    for component in bootstrap.COMPONENTS:
        directory = native / 'configured/DEVELOPMENT' / component
        bootstrap.configure(source, Path(context['tool']), directory, component=component)
        configured.append(dict(variant='DEVELOPMENT', component=component,
                               makefile_sha256=sha(directory / 'Makefile'),
                               headers={path.name: sha(path) for path in sorted(directory.glob('*.h'))}))
    bootstrap.write_json(native / 'configure-result.json', dict(configured=configured,
                         source_directory=source.relative_to(ROOT).as_posix(), source_commit=XNU_COMMIT))

    result['stage'] = 'native-header-generation'
    cloud_compile.download(FIREHOSE_URL, ROOT / 'host-tools/opensource-declarations/os/firehose_buffer_private.h',
                           FIREHOSE_SHA256)
    cloud_compile.sdk_declarations()
    export_source_headers.main()
    generate_link_metadata.main()
    generate_native_mig.main()
    generate_native_extra.main()
    result['fresh_generated_headers'] = fresh_headers(native)
    result.update(stage='complete', passed=True, native_inputs_generated=True)
