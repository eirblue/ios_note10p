"""Manual macOS CI entry point. Source-only compile audit; never a flash build."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from prepare_build_selection import ROOT

COMMIT = 'ac9718fb1af618d5ce8678d0dc6e8a58f252216f'
SOURCE_SHA = '577f4a220304296332e28c802779e7b5e6a27a46812315aacf61c0269a03e12a'
KDK_URL = 'https://github.com/dortania/KdkSupportPkg/releases/download/25F71/Kernel_Debug_Kit_26.5_build_25F71.dmg'
KDK_SHA = '90ed319cd1ba6e23d1eefcee89fa1b10743f4cf60b85208ae52aa9f45543c7aa'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b''):digest.update(block)
    return digest.hexdigest()


def download(url, path, expected):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url, timeout=60) as response, path.open('wb') as stream:
            shutil.copyfileobj(response, stream, 1024 * 1024)
    if sha(path) != expected:raise ValueError('Download hash mismatch: ' + path.name)


def prepare_source_and_master():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    if target['public_reference_commit'] != COMMIT:raise ValueError('Cloud recipe must be updated for a new source commit')
    research = ROOT / target['research_directory']; research.mkdir(parents=True, exist_ok=True)
    archive = research / 'xnu-12377.121.6.tar.gz'
    url = 'https://codeload.github.com/apple-oss-distributions/xnu/tar.gz/' + COMMIT
    download(url, archive, SOURCE_SHA)
    directory = research / 'xnu-reference'
    if not (directory / ('xnu-' + COMMIT) / 'config/MASTER').exists():
        with tarfile.open(archive) as package:package.extractall(directory, filter='data')
    source = directory / ('xnu-' + COMMIT)
    reference = {'tag': target['public_reference_tag'], 'commit': COMMIT, 'url': url,
                 'archive_sha256': SOURCE_SHA, 'source_directory': source.relative_to(ROOT).as_posix(),
                 'target_kernel': target['kernel_version'], 'exact_match': False}
    (research / 'xnu-reference.json').write_text(json.dumps(reference, indent=2))
    stage = ROOT / 'note10/private/cloud-master-source'; stage.mkdir(parents=True, exist_ok=True)
    soc = stage / 'config/MASTER.arm64.exynos9825'
    if soc.exists():soc.unlink()
    subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '--include=*MASTER.arm64.exynos9825',
                    '--directory', stage.relative_to(ROOT).as_posix(),
                    'note10/xnu26/patches/0006-exynos9825-master-link-input.patch'], cwd=ROOT, check=True)
    text = (source / 'SETUP/config/doconf').read_text()
    start = text.index('    sed -n \\\n'); end = text.index("' >$SYSCONF.new", start) + 1
    selector = 'export PATH=/usr/bin:/bin\n' + text[start:end]
    global_master = (source / 'config/MASTER').read_bytes(); master = soc.read_bytes()
    import re
    if re.search(rb'^#(?:if|else|elif|endif)\b', global_master + master, re.MULTILINE):
        raise ValueError('Unresolved MASTER condition in cloud input')
    output = ROOT / 'note10/private/xnu26-master'; output.mkdir(parents=True, exist_ok=True)
    cases = []
    for variant in ('RELEASE', 'DEVELOPMENT', 'DEBUG'):
        data = global_master + master + ('\n+' + variant + '\n').encode() + global_master + master
        result = subprocess.run(['/bin/sh', '-c', selector], input=data, capture_output=True, check=True)
        path = output / ('config.' + variant + '_ARM64'); path.write_bytes(result.stdout)
        cases.append({'variant': variant, 'text_sha256': sha(path)})
    (output / 'test-result.json').write_text(json.dumps({'config_texts': cases, 'cloud_selection_only': True}, indent=2))


def sdk_declarations():
    sys.path.insert(0, str(ROOT / 'note10'))
    from extract_kdk_headers import xar_payloads, extract
    image = ROOT / 'host-tools/kdk/Kernel_Debug_Kit_26.5_build_25F71.dmg'
    download(KDK_URL, image, KDK_SHA)
    mount = ROOT / 'host-tools/kdk/cloud-mount'; mount.mkdir(parents=True, exist_ok=True)
    subprocess.run(['hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', str(mount), str(image)], check=True)
    try:
        # CE V2/Kernel.h lives in KernelSupport in KDK.pkg, while the API
        # declarations are in KDK_SDK.pkg. Both payloads are needed.
        for payload in xar_payloads(mount / 'KernelDebugKit.pkg'):
            extract(payload)
    finally:
        subprocess.run(['hdiutil', 'detach', str(mount)], check=True)


def main():
    if sys.platform != 'darwin':raise SystemExit('This manual cloud entry point requires macOS/Xcode')
    compiler = subprocess.check_output(['xcrun', '-f', 'clang']).decode().strip()
    sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path']).decode().strip()
    probe = subprocess.run([compiler, '--target=arm64-apple-darwin', '-E', '-P', '-x', 'c', '-'],
                           input='#if __has_builtin(__builtin_xnu_type_summary)\nsummary_supported\n#endif\n#if __has_builtin(__builtin_xnu_types_compatible)\ncompatible_supported\n#endif\n',
                           capture_output=True, text=True, check=True)
    toolchain = {'compiler': compiler, 'sdk': sdk,
                 'compiler_version': subprocess.check_output([compiler, '--version']).decode(),
                 'xnu_type_summary': 'summary_supported' in probe.stdout,
                 'xnu_types_compatible': 'compatible_supported' in probe.stdout}
    report = ROOT / 'note10/private/cloud-toolchain-result.json'
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(toolchain, indent=2))
    print(json.dumps(toolchain), flush=True)
    prepare_source_and_master()
    from probe_kernel_headers import generated_headers
    target = json.loads((ROOT / 'note10/target.json').read_text())
    generated_headers(ROOT / target['research_directory'])
    sdk_declarations()
    download('https://raw.githubusercontent.com/apple-oss-distributions/libdispatch/2361ffb78a76f7ee488cd052eb0bc5c767118bf9/os/firehose_buffer_private.h',
             ROOT / 'host-tools/opensource-declarations/os/firehose_buffer_private.h',
             'b1da2269d930974d1fb122d90446534553829dc2a3b090b3d0ea0813fd95dd45')
    env = dict(os.environ)
    env['N10_CC'] = compiler
    env['N10_SDKROOT'] = sdk
    env['N10_MAKE'] = shutil.which('make')
    for script in ('build_windows_config.py', 'configure_windows_xnu.py', 'export_source_headers.py', 'generate_native_mig.py'):
        subprocess.run([sys.executable, str(Path(__file__).parent / script)], cwd=ROOT, env=env, check=True)
    mode = ['--all-c'] if '--all-c' in sys.argv[1:] else []
    subprocess.run([sys.executable, str(Path(__file__).parent / 'compile_native_components.py'), *mode],
                   cwd=ROOT, env=env, check=True)


if __name__ == '__main__':
    main()
