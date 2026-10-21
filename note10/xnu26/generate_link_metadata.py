"""Stamp native build metadata using XNU's real newvers.pl and pinned KDK version."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
from prepare_build_selection import ROOT


def main():
    if sys.platform != 'darwin':raise SystemExit('Native metadata generation requires macOS')
    private = ROOT / 'note10/private/windows-xnu'
    config = json.loads((private / 'configure-result.json').read_text())
    source = ROOT / config['source_directory']
    info = ROOT / 'host-tools/kdk/headers/KDK.pkg/System/Library/Extensions/System.kext/Info.plist'
    version = plistlib.loads(info.read_bytes())['CFBundleVersion']
    output = private / 'native-link'; output.mkdir(exist_ok=True)
    (output / 'xnuVersion').write_text(version + '\n')
    header = output / 'include/libkern/version.h'; header.parent.mkdir(parents=True, exist_ok=True)
    cfile = output / 'version.c'
    shutil.copyfile(source / 'libkern/libkern/version.h.template', header)
    shutil.copyfile(source / 'config/version.c.template', cfile)
    env = dict(os.environ, SRCROOT=str(source), OBJROOT=str(output), TARGET=str(output),
               CURRENT_KERNEL_CONFIG_LC='development',
               KERNEL_BUILD_OBJROOT='note10-source-xnu-12377.121.6/DEVELOPMENT_ARM64_EXYNOS9825')
    result = subprocess.run(['perl', str(source / 'config/newvers.pl'), str(header), str(cfile)],
                            cwd=source, env=env, capture_output=True, text=True, check=True)
    (output / 'generate-version.log').write_text(result.stdout + result.stderr)
    if '###KERNEL_' in header.read_text() + cfile.read_text():raise ValueError('Unstamped version token')
    report = {'darwin_version': version, 'darwin_version_source': str(info.relative_to(ROOT)),
              'darwin_version_source_sha256': hashlib.sha256(info.read_bytes()).hexdigest(),
              'source_xnu_version': '12377.121.6', 'target_ipsw_xnu_version': '12377.122.8',
              'exact_target_source': False,
              'newvers_sha256': hashlib.sha256((source / 'config/newvers.pl').read_bytes()).hexdigest(),
              'version_header_sha256': hashlib.sha256(header.read_bytes()).hexdigest(),
              'version_c_sha256': hashlib.sha256(cfile.read_bytes()).hexdigest()}
    (output / 'generate-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'native_version_stamped': True, 'darwin_version': version, 'exact_target_source': False}), flush=True)


if __name__ == '__main__':main()
