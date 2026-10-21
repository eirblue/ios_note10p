"""Supply real generic ARM interfaces and a conservative Exynos policy.

Replays the preceding series in a private minimal tree, then validates patch 9.
No Apple support binary is copied into the target. Hardware sleep, production
fuses and Exynos register tuning are not established by these source changes.
"""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
from prepare_build_selection import ROOT, replace_one

PINS = {
    'osfmk/arm64/caches_asm.s': '1ee90140c81655f6e5eced4049f0887e3f75f6d8e77a491c8a36531e3db6d328',
    'osfmk/arm64/start.s': 'a5c1a95b087f62f9e548bed7a0274cf420af1d69bfd656c1481d629093e2b07a',
    'osfmk/arm/pmap/pmap.h': '90eb47769ca63b300cb4f589c6121a2bb1553c0f704b10c5af2e042cc4d8bc55',
    'osfmk/arm64/arm_vm_init.c': '9e17da181e72144d27df4ce256988226bfef0e41c0744fc9ef6466f0844c2a32',
    'osfmk/arm64/genassym.c': 'e2ca4b5c8d0c05d63408fb9cb88365733056fbb3cf8dfe448750fc854bedd263',
}


def main():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    reference = json.loads((ROOT / target['research_directory'] / 'xnu-reference.json').read_text())
    source = ROOT / reference['source_directory']
    patches = ROOT / 'note10/xnu26/patches'
    filename = '0009-exynos9825-generic-native-interfaces.patch'
    names = [s for s in (patches / 'series').read_text().splitlines() if s and not s.startswith('#') and s != filename]
    paths = set(PINS) | {'pexpert/conf/files.arm64', 'pexpert/arm/note10/production_policy.c'}
    for name in names:
        for line in (patches / name).read_text().splitlines():
            if line.startswith(('--- a/', '+++ b/')):paths.add(line[6:])
    stage = ROOT / 'note10/private/xnu26-native-interfaces/stage'
    pristine = {}
    for name in paths:
        p = Path(name)
        if p.is_absolute() or '..' in p.parts or '.git' in p.parts:raise ValueError('Unsafe series input')
        original = source / name
        raw = original.read_bytes() if original.is_file() else None
        if name in PINS and hashlib.sha256(raw).hexdigest() != PINS[name]:raise ValueError('Native interface pin changed')
        pristine[name] = raw
        out = stage / name; out.parent.mkdir(parents=True, exist_ok=True)
        if raw is not None:out.write_bytes(raw)
        elif out.exists():out.unlink()
    command = ['git', '-c', 'core.autocrlf=false', 'apply', '--directory', stage.relative_to(ROOT).as_posix()]
    for name in names:subprocess.run([*command, (patches / name).relative_to(ROOT).as_posix()], cwd=ROOT, check=True)
    changed = set(PINS) | {'pexpert/conf/files.arm64', 'pexpert/arm/note10/production_policy.c'}
    old = {n: (stage / n).read_text() if (stage / n).exists() else '' for n in changed}
    new = dict(old)
    n = 'osfmk/arm64/caches_asm.s'
    new[n] = replace_one(new[n], 'LEXT(CleanPoC_Dcache)\n',
        '#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\nLEXT(clean_mmu_dcache)\n#endif\nLEXT(CleanPoC_Dcache)\n')
    new[n] = replace_one(new[n], 'LEXT(CleanPoC_DcacheRegion_internal)\n',
        '#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n'
        '\t.globl EXT(CleanPoC_DcacheRegion_Force_nopreempt_nohid)\n'
        'LEXT(CleanPoC_DcacheRegion_Force_nopreempt_nohid)\n#endif\n'
        'LEXT(CleanPoC_DcacheRegion_internal)\n')
    n = 'osfmk/arm64/start.s'
    new[n] = replace_one(new[n], '#if WITH_CLASSIC_S2R\nLEXT(SleepToken)',
        '#if WITH_CLASSIC_S2R || defined(ARM64_BOARD_CONFIG_EXYNOS9825)\nLEXT(SleepToken)')
    n = 'osfmk/arm64/genassym.c'
    new[n] = replace_one(new[n], '#if WITH_CLASSIC_S2R\n\tDECLARE("stSize", sizeof(SleepToken));',
        '#if WITH_CLASSIC_S2R || defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n\tDECLARE("stSize", sizeof(SleepToken));')
    n = 'osfmk/arm/pmap/pmap.h'
    new[n] = replace_one(new[n], '#if SCHED_HYGIENE_DEBUG && (DEBUG || DEVELOPMENT)\nbool pmap_pending_preemption',
        '#if SCHED_HYGIENE_DEBUG && (DEBUG || DEVELOPMENT) && !defined(ARM64_BOARD_CONFIG_EXYNOS9825)\nbool pmap_pending_preemption')
    n = 'osfmk/arm64/arm_vm_init.c'
    new[n] = replace_one(new[n], '\tml_enable_monitor();',
        '#if !defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n\tml_enable_monitor();\n'
        '#endif /* No legacy Apple monitor interface on Exynos. */')
    new['pexpert/conf/files.arm64'] += '\npexpert/arm/note10/production_policy.c standard\n'
    new['pexpert/arm/note10/production_policy.c'] = (ROOT / 'note10/xnu26/production_policy.c').read_text()
    diff = ''.join(''.join(difflib.unified_diff(old[n].splitlines(True), new[n].splitlines(True),
                fromfile='a/' + n if old[n] else '/dev/null', tofile='b/' + n)) for n in sorted(changed))
    patch = patches / filename; patch.write_text(diff, newline='\n')
    rel = patch.relative_to(ROOT).as_posix()
    subprocess.run([*command, '--check', rel], cwd=ROOT, check=True)
    subprocess.run([*command, rel], cwd=ROOT, check=True)
    for n in changed:
        if (stage / n).read_bytes() != new[n].encode():raise ValueError('Native interface patch differs')
    subprocess.run([*command, '--reverse', rel], cwd=ROOT, check=True)
    for name in reversed(names):subprocess.run([*command, '--reverse', (patches / name).relative_to(ROOT).as_posix()], cwd=ROOT, check=True)
    for n, raw in pristine.items():
        if raw is None:
            if (stage / n).exists():raise ValueError('Added source remains after reverse')
        elif (stage / n).read_bytes() != raw:raise ValueError('Original stage not restored')
        if (source / n).is_file() and (source / n).read_bytes() != raw:raise ValueError('Pristine reference changed')
    report = {'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
              'preceding_patches': names, 'sequential_apply_reverse_passed': True,
              'patched_source_sha256': {n: hashlib.sha256(t.encode()).hexdigest() for n,t in new.items()},
              'cache_operations_use_existing_generic_arm_code': True,
              'preemption_uses_existing_ast_urgent_poll': True,
              'fuse_measurement_performed': False, 'unknown_fuse_policy': 'production restrictions',
              'hardware_sleep_implemented': False, 'whole_kernel_build': False}
    (stage.parent / 'patch-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'files': len(changed), 'full_series_apply_reverse_passed': True}))


if __name__ == '__main__':main()
