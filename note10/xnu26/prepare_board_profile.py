"""Generate the parameterized Exynos header patch; never invent hardware values."""
import difflib
import hashlib
import json
import subprocess
from prepare_build_selection import ROOT, replace_one

PINS = {
    'pexpert/pexpert/arm64/board_config.h': '147ea1c2e2e23b7844dcebe3ae099f1443505997acb8063da309827b2fb299be',
    'osfmk/arm64/proc_reg.h': 'fcbead4162ad09d0f51be9ce88e5f2d6d89e89e58934975ee1aa23e506485055',
}


def main():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    research = ROOT / target['research_directory']
    reference = json.loads((research / 'xnu-reference.json').read_text())
    source = ROOT / reference['source_directory']
    old = {}
    for name, pin in PINS.items():
        raw = (source / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin:
            raise ValueError('Pinned board input changed: ' + name)
        old[name] = raw.decode('utf-8')
    new = dict(old)
    name = 'pexpert/pexpert/arm64/board_config.h'
    new[name] = replace_one(old[name], '#ifdef ARM64_BOARD_CONFIG_VMAPPLE\n',
        '#ifdef ARM64_BOARD_CONFIG_EXYNOS9825\n#include <pexpert/arm64/EXYNOS9825.h>\n#endif\n\n'
        '#ifdef ARM64_BOARD_CONFIG_VMAPPLE\n')
    name = 'osfmk/arm64/proc_reg.h'
    new[name] = replace_one(old[name], '#elif defined (VMAPPLE)\n',
        '#elif defined (ARM64_BOARD_CONFIG_EXYNOS9825)\n'
        '/* Required explicit inputs from the Note10 compile profile. */\n'
        '#define MMU_I_CLINE N10_ICACHE_LINE_LOG2\n#define MMU_CLINE N10_DCACHE_LINE_LOG2\n\n'
        '#elif defined (VMAPPLE)\n')
    name = 'pexpert/pexpert/arm64/EXYNOS9825.h'
    old[name] = ''
    new[name] = (ROOT / 'note10/xnu26/EXYNOS9825.h').read_text(encoding='utf-8')
    patch = ''.join(''.join(difflib.unified_diff(old[n].splitlines(True), new[n].splitlines(True),
                    fromfile='a/' + n if old[n] else '/dev/null', tofile='b/' + n)) for n in old)
    patch_file = ROOT / 'note10/xnu26/patches/0005-exynos9825-explicit-board-profile.patch'
    patch_file.write_text(patch, encoding='utf-8', newline='\n')
    private = ROOT / 'note10/private/xnu26-board'
    stage = private / 'stage'
    for name, body in old.items():
        path = stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if body:
            path.write_text(body, encoding='utf-8', newline='\n')
        elif path.exists():
            path.unlink()
    command = ['git', '-c', 'core.autocrlf=false', 'apply', '--directory', stage.relative_to(ROOT).as_posix()]
    relative_patch = patch_file.relative_to(ROOT).as_posix()
    subprocess.run([*command, '--check', relative_patch], cwd=ROOT, check=True)
    subprocess.run([*command, relative_patch], cwd=ROOT, check=True)
    for name, body in new.items():
        if (stage / name).read_bytes() != body.encode():
            raise ValueError('Applied board patch differs')
        path = private / 'patched-inputs' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8', newline='\n')
    subprocess.run([*command, '--reverse', relative_patch], cwd=ROOT, check=True)
    for name, body in old.items():
        for root in (stage, source):
            path = root / name
            if (path.read_bytes() != body.encode()) if body else path.exists():
                raise ValueError('Original board source not preserved')
    report = {'source_commit': reference['commit'], 'source_sha256': PINS,
              'patch_sha256': hashlib.sha256(patch_file.read_bytes()).hexdigest(),
              'files': {n: hashlib.sha256(body.encode()).hexdigest() for n, body in new.items()},
              'apply_reverse_passed': True, 'source_unchanged': True,
              'physical_profile_values_supplied': False, 'whole_kernel_build': False}
    (private / 'patch-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'files': len(new), 'apply_reverse_passed': True, 'hardware_defaults': False}))


if __name__ == '__main__':
    main()
