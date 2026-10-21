"""Exclude unused Apple core-type helpers from two generic Exynos units."""
import difflib
import hashlib
import json
import subprocess
from prepare_build_selection import ROOT, replace_one


def main():
    relative = 'osfmk/arm64/sleh.c'
    bridge = ROOT / 'note10/private/xnu26-irq'
    metadata = json.loads((bridge / 'patch-result.json').read_text())
    raw = (bridge / 'patched-inputs' / relative).read_bytes()
    if hashlib.sha256(raw).hexdigest() != metadata['component_sha256'][relative]:
        raise ValueError('Preceding IRQ exception source changed')
    old = raw.decode()
    new = replace_one(old, '#include <pexpert/arm64/apple_arm64_cpu.h>',
        '#if !defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n'
        '#include <pexpert/arm64/apple_arm64_cpu.h>\n#endif')
    patch = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                    fromfile='a/' + relative, tofile='b/' + relative))
    target = json.loads((ROOT / 'note10/target.json').read_text())
    reference = json.loads((ROOT / target['research_directory'] / 'xnu-reference.json').read_text())
    common_relative = 'osfmk/arm/machine_routines_common.c'
    common_raw = (ROOT / reference['source_directory'] / common_relative).read_bytes()
    common_old = common_raw.decode()
    common_new = replace_one(common_old, '#include <pexpert/arm64/apple_arm64_cpu.h>',
        '#if !defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n'
        '#include <pexpert/arm64/apple_arm64_cpu.h>\n#endif')
    patch += ''.join(difflib.unified_diff(common_old.splitlines(True), common_new.splitlines(True),
                    fromfile='a/' + common_relative, tofile='b/' + common_relative))
    path = ROOT / 'note10/xnu26/patches/0007-exynos9825-exception-header-scope.patch'
    path.write_text(patch, encoding='utf-8', newline='\n')
    private = ROOT / 'note10/private/xnu26-exception'
    stage = private / 'stage'
    (stage / relative).parent.mkdir(parents=True, exist_ok=True)
    (stage / relative).write_bytes(raw)
    (stage / common_relative).parent.mkdir(parents=True, exist_ok=True)
    (stage / common_relative).write_bytes(common_raw)
    command = ['git', '-c', 'core.autocrlf=false', 'apply', '--directory', stage.relative_to(ROOT).as_posix()]
    subprocess.run([*command, '--check', path.relative_to(ROOT).as_posix()], cwd=ROOT, check=True)
    subprocess.run([*command, path.relative_to(ROOT).as_posix()], cwd=ROOT, check=True)
    if (stage / relative).read_bytes() != new.encode():raise ValueError('Exception patch differs')
    if (stage / common_relative).read_bytes() != common_new.encode():raise ValueError('Common source patch differs')
    subprocess.run([*command, '--reverse', path.relative_to(ROOT).as_posix()], cwd=ROOT, check=True)
    if (stage / relative).read_bytes() != raw:raise ValueError('Exception patch reverse differs')
    if (stage / common_relative).read_bytes() != common_raw:raise ValueError('Common source reverse differs')
    report = {'preceding_bridge_patch_sha256': metadata['patch_sha256'],
              'patch_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'patched_source_sha256': hashlib.sha256(new.encode()).hexdigest(),
              'common_source_sha256': hashlib.sha256(common_new.encode()).hexdigest(),
              'apply_reverse_passed': True, 'whole_kernel_build': False}
    private.mkdir(exist_ok=True)
    (private / 'patch-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'files': 2, 'apply_reverse_passed': True}))


if __name__ == '__main__':
    main()
