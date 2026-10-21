"""Validate manual workflow shape and its source/master preparation on a PC.

The macOS job itself is not executed or authenticated by this test.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from prepare_build_selection import ROOT
import cloud_compile


def main():
    sys.path.insert(0, str(ROOT / 'host-tools/python-packages'))
    import yaml
    workflow = ROOT / '.github/workflows/note10-native-compile.yml'
    document = yaml.safe_load(workflow.read_text())
    triggers = document.get('on', document.get(True))
    if set(triggers) != {'workflow_dispatch'} or document['permissions'] != {'contents': 'read'}:
        raise ValueError('Cloud job must remain manual/read-only')
    job = document['jobs']['compile']
    if job['runs-on'] != 'macos-26' or job['timeout-minutes'] > 30:
        raise ValueError('Unexpected runner or job limit')
    upload = job['steps'][-1]['with']['path']
    if any(s in upload for s in ('*.ipsw', '*.dmg', '*.h', 'host-tools/', 'origin_firmware/')):
        raise ValueError('Cloud artifact path includes original firmware/SDK content')
    fixture = ROOT / 'note10/private/cloud-input-test'
    (fixture / 'note10/xnu26/patches').mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'init', '-q', str(fixture)], check=True)
    shutil.copyfile(ROOT / 'note10/target.json', fixture / 'note10/target.json')
    name = '0006-exynos9825-master-link-input.patch'
    shutil.copyfile(ROOT / 'note10/xnu26/patches' / name, fixture / 'note10/xnu26/patches' / name)
    target = json.loads((ROOT / 'note10/target.json').read_text())
    research = fixture / target['research_directory']; research.mkdir(parents=True, exist_ok=True)
    archive = 'xnu-12377.121.6.tar.gz'
    shutil.copyfile(ROOT / target['research_directory'] / archive, research / archive)
    cloud_compile.ROOT = fixture
    original_run = subprocess.run
    def local_shell(command, **kwargs):
        if command[:2] == ['/bin/sh', '-c']:
            command = [r'C:/Program Files/Git/bin/bash.exe', '--noprofile', '--norc', '-c', command[2]]
        return original_run(command, **kwargs)
    subprocess.run = local_shell
    try:
        cloud_compile.prepare_source_and_master()
    finally:
        subprocess.run = original_run; cloud_compile.ROOT = ROOT
    for variant in ('RELEASE', 'DEVELOPMENT', 'DEBUG'):
        name = 'config.' + variant + '_ARM64'
        if (fixture / 'note10/private/xnu26-master' / name).read_bytes() != (ROOT / 'note10/private/xnu26-master' / name).read_bytes():
            raise ValueError('Cloud MASTER output differs: ' + variant)
    report = {'workflow_sha256': hashlib.sha256(workflow.read_bytes()).hexdigest(),
              'workflow_manual_only': True, 'firmware_sdk_excluded_from_upload': True,
              'master_output_variants_matched': 3, 'source_archive_hash_checked': True,
              'macos_job_executed': False, 'github_authentication_checked': False}
    (ROOT / 'note10/private/cloud-recipe-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
