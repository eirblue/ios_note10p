"""Read-only host/source build audit; old patch checks are independent, not cumulative."""
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    research = ROOT / target['research_directory']
    reference = json.loads((research / 'xnu-reference.json').read_text())
    source = ROOT / reference['source_directory']
    definitions = (source / 'makedefs/MakeInc.def').read_text()
    machines = re.findall(r'^SUPPORTED_ARM64_MACHINE_CONFIGS\s*=\s*(.+)$', definitions, re.M)
    host_tools = {name: shutil.which(name) for name in ('make','xcrun','xcodebuild','git')}
    ndk_make = Path(r'C:/Program Files/Unity/Hub/Editor/2021.3.20f1/Editor/Data/PlaybackEngines/AndroidPlayer/NDK/prebuilt/windows-x86_64/bin/make.exe')
    host_tools['ndk_make'] = str(ndk_make) if ndk_make.is_file() else None
    checks = []
    for patch in sorted((ROOT / 'xnu/patches').glob('*.patch')):
        result = subprocess.run(['git','apply','--check','--directory',source.relative_to(ROOT).as_posix(),
                                 patch.relative_to(ROOT).as_posix()],cwd=ROOT,capture_output=True,text=True)
        checks.append({'patch':patch.name,'applies_independently_to_pristine_reference':result.returncode == 0,
                       'diagnostic':result.stderr.strip()[:1500]})
    applied = sum(c['applies_independently_to_pristine_reference'] for c in checks)
    result = {'host':platform.system(),'tools':host_tools,'reference':reference,
        'arm64_machine_config_declarations':machines,
        'note10_machine_config_present':'EXYNOS9825' in definitions or 'NOTE10' in definitions,
        'forced_platform_support_archive':'System/Library/KernelSupport/lib$(CURRENT_MACHINE_CONFIG)' in definitions,
        'firehose_required':'-lfirehose_kernel' in definitions,
        'old_patch_checks':{'total':len(checks),'independent_success':applied,'independent_failure':len(checks)-applied,
                            'scope':'Each patch checked separately against pristine source, no patch applied.',
                            'patches':checks},
        'full_build_attempted':False,
        'blockers':['No configured macOS/Xcode/SDK/KDK build environment on this Windows host.',
                    'Public reference differs from the active IPSW kernel.',
                    'No Exynos9825 machine/platform configuration or hardware integration.',
                    'Apple platform support libraries cannot be treated as Exynos drivers.']}
    (research / 'xnu-build-audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ('host','tools','arm64_machine_config_declarations',
                     'note10_machine_config_present','full_build_attempted')}))
    print(json.dumps({'old_patch_checks':len(checks),'independent_success':applied,'independent_failure':len(checks)-applied}))

if __name__ == '__main__': main()
