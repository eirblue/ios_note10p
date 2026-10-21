"""Scope Apple-only architecture dependencies out of the Exynos candidates.

Does not implement Samsung DMA protection, CPU tuning or a complete boot path.
"""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
from prepare_build_selection import ROOT, replace_one

PINS = {
    'osfmk/arm/pmap/pmap.c': '90312d444fae75ef692106aa0ce755bfcf046395fe39d0c8bda72077d2adb9f0',
    'osfmk/arm64/pcb.c': 'c613043ca556468a25f51c6711efac6d98250efec64c49cc0839c4dc11d313be',
    'osfmk/arm64/start.s': 'a5c1a95b087f62f9e548bed7a0274cf420af1d69bfd656c1481d629093e2b07a',
}


def main():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    reference = json.loads((ROOT / target['research_directory'] / 'xnu-reference.json').read_text())
    source = ROOT / reference['source_directory']
    old = {}
    for name, expected in PINS.items():
        raw = (source / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:raise ValueError('Architecture source pin changed')
        old[name] = raw.decode()
    new = dict(old)
    name = 'osfmk/arm/pmap/pmap.c'
    new[name] = replace_one(new[name], '#include <arm64/ppl/sart.h>\n#include <arm64/ppl/uat.h>',
        '#if !defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n'
        '#include <arm64/ppl/sart.h>\n#include <arm64/ppl/uat.h>\n#endif')
    new[name] = replace_one(new[name], '\tsart_bootstrap();',
        '#if !defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n\tsart_bootstrap();\n'
        '#else\n\t/* Exynos has no Apple SART. Samsung DMA protection is not implemented here. */\n#endif')
    name = 'osfmk/arm64/pcb.c'
    new[name] = replace_one(new[name], '#include <pexpert/arm64/apple_arm64_cpu.h>',
        '#if !defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n'
        '#include <pexpert/arm64/apple_arm64_cpu.h>\n#endif')
    name = 'osfmk/arm64/start.s'
    new[name] = replace_one(new[name], '#include <arm64/tunables/tunables.s>',
        '#if !defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n'
        '#include <arm64/tunables/tunables.s>\n#endif')
    new[name] = replace_one(new[name], '\tAPPLY_TUNABLES x12, x13, x14',
        '#if !defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n\tAPPLY_TUNABLES x12, x13, x14\n'
        '#endif /* Apple per-SoC tuning is not applicable to Exynos. */')
    patch = ''.join(''.join(difflib.unified_diff(old[n].splitlines(True), new[n].splitlines(True),
                    fromfile='a/' + n, tofile='b/' + n)) for n in old)
    path = ROOT / 'note10/xnu26/patches/0008-exynos9825-architecture-dependencies.patch'
    path.write_text(patch, newline='\n')
    private = ROOT / 'note10/private/xnu26-architecture'
    stage = private / 'stage'
    for name, text in old.items():
        p = stage / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(text.encode())
    command = ['git', '-c', 'core.autocrlf=false', 'apply', '--directory', stage.relative_to(ROOT).as_posix()]
    subprocess.run([*command, '--check', path.relative_to(ROOT).as_posix()], cwd=ROOT, check=True)
    subprocess.run([*command, path.relative_to(ROOT).as_posix()], cwd=ROOT, check=True)
    for name, text in new.items():
        if (stage / name).read_bytes() != text.encode():raise ValueError('Architecture patch differs')
    subprocess.run([*command, '--reverse', path.relative_to(ROOT).as_posix()], cwd=ROOT, check=True)
    for name, text in old.items():
        if (stage / name).read_bytes() != text.encode():raise ValueError('Architecture reverse differs')
    report = {'patch_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'original_source_sha256': PINS,
              'patched_source_sha256': {n: hashlib.sha256(t.encode()).hexdigest() for n,t in new.items()},
              'sequential_apply_reverse_passed': True, 'exynos_dma_protection_implemented': False,
              'hardware_cpu_tuning_verified': False, 'whole_kernel_build': False}
    (private / 'patch-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'files': len(new), 'apply_reverse_passed': True, 'whole_kernel_build': False}))


if __name__ == '__main__':main()
