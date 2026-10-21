"""Compile actual XNU headers with synthetic board inputs, never a hardware profile."""
import hashlib
import json
import re
import subprocess
from prepare_build_selection import ROOT
from probe_kernel_headers import context


def main():
    reference, _, _, compiler, common, _ = context()
    private = ROOT / 'note10/private/xnu26-board'
    tree = private / 'patched-inputs'
    manifest = json.loads((private / 'patch-result.json').read_text())
    for name, digest in manifest['files'].items():
        if hashlib.sha256((tree / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Board patch input changed: ' + name)
    # Overlay only the actual patched board/proc headers ahead of pristine includes.
    prefix = ['-I', str(tree / 'pexpert'), '-I', str(tree / 'osfmk')]
    unit = private / 'headers.c'
    unit.write_text('#include <machine/machine_routines.h>\n#include <mach/vm_types.h>\n'
                    '#include <kern/debug.h>\n#include <pexpert/pexpert.h>\n'
                    '#include <pexpert/device_tree.h>\n'
                    '_Static_assert(MAX_CPUS == 1 && MAX_CPU_CLUSTERS == 1, "single CPU profile");\n'
                    '_Static_assert(MMU_I_CLINE == N10_ICACHE_LINE_LOG2, "instruction line");\n'
                    '_Static_assert(MMU_CLINE == N10_DCACHE_LINE_LOG2, "data line");\n', newline='\n')
    with unit.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write('_Static_assert(ARM_PGSHIFT == N10_KERNEL_PAGE_SHIFT, "hardware page shift");\n')
    values = {'N10_BOARD_SCHEMA': 1, 'N10_ICACHE_LINE_LOG2': 6, 'N10_DCACHE_LINE_LOG2': 6,
              'N10_MAX_CACHE_LINE_LOG2': 7, 'N10_KERNEL_PAGE_SHIFT': 14}
    cases = [('synthetic_16k', {}, None), ('synthetic_4k', {'N10_KERNEL_PAGE_SHIFT': 12}, None),
             ('synthetic_larger_line', {'N10_DCACHE_LINE_LOG2': 7}, None),
             ('missing_schema', {'N10_BOARD_SCHEMA': None}, 'explicit board schema'),
             ('wrong_schema', {'N10_BOARD_SCHEMA': 2}, 'explicit board schema'),
             ('missing_icache', {'N10_ICACHE_LINE_LOG2': None}, 'explicit cache/page'),
             ('missing_dcache', {'N10_DCACHE_LINE_LOG2': None}, 'explicit cache/page'),
             ('missing_maximum', {'N10_MAX_CACHE_LINE_LOG2': None}, 'explicit cache/page'),
             ('missing_pages', {'N10_KERNEL_PAGE_SHIFT': None}, 'explicit cache/page'),
             ('line_too_small', {'N10_DCACHE_LINE_LOG2': 3}, 'out of range'),
             ('line_too_large', {'N10_ICACHE_LINE_LOG2': 12}, 'out of range'),
             ('maximum_too_small', {'N10_MAX_CACHE_LINE_LOG2': 5}, 'maximum cache line'),
             ('unsupported_pages', {'N10_KERNEL_PAGE_SHIFT': 16}, 'only 4K or 16K'),
             ('pac_build', {'__arm64e__': 1}, 'plain ARM64 kernel'),
             ('pac_feature', {'HAS_APPLE_PAC': 1}, 'plain ARM64 kernel'),
             ('bti_build', {'XNU_BUILT_WITH_BTI': 1}, 'plain ARM64 kernel'),
             ('apple_family', {'APPLE_ARM64_ARCH_FAMILY': 1}, 'cannot inherit Apple'),
             ('apple_smp', {'USE_APPLEARMSMP': 1}, 'cannot inherit Apple'),
             ('gicv3', {'HAS_GIC_V3': 1}, 'cannot inherit Apple'),
             ('apple_timer', {'HAS_APPLE_GENERIC_TIMER': 1}, 'cannot inherit Apple'),
             ('sptm', {'CONFIG_SPTM': 1}, 'monitor and SPTM'),
             ('monitor', {'XNU_MONITOR': 1}, 'monitor and SPTM')]
    results = []
    for name, overrides, expected in cases:
        inputs = dict(values); inputs.update(overrides)
        defines = ['-D' + k + '=' + str(v) for k, v in inputs.items() if v is not None]
        command = [str(compiler), *prefix, *common, '-DARM64_BOARD_CONFIG_EXYNOS9825', *defines, str(unit)]
        result = subprocess.run(command, capture_output=True, timeout=60)
        log = private / (name + '.log'); log.write_bytes(result.stdout + result.stderr)
        diagnostics = result.stderr.decode('utf-8', errors='replace')
        passed = (result.returncode == 0) if expected is None else (result.returncode != 0 and expected in diagnostics)
        results.append({'name': name, 'passed': passed, 'syntax_passed': result.returncode == 0,
                        'expected_error': expected, 'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
        if not passed:
            print(diagnostics)
    objects = []
    bridge_tree = ROOT / 'note10/private/xnu26-irq/patched-inputs'
    bootstrap_tree = ROOT / 'note10/private/xnu26-bootstrap/patched-inputs'
    bridge_manifest = json.loads((bridge_tree.parent / 'patch-result.json').read_text())
    bootstrap_manifest = json.loads((bootstrap_tree.parent / 'patch-result.json').read_text())
    for root, key, metadata in ((bridge_tree, 'component_sha256', bridge_manifest),
                                (bootstrap_tree, 'files', bootstrap_manifest)):
        for name, expected in metadata[key].items():
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
                raise ValueError('Dependent XNU patch input changed: ' + name)
    component_flags = [f for f in common if f != '-fsyntax-only']
    component_prefix = [*prefix, '-I', str(bridge_tree / 'osfmk'),
                        '-I', str(bootstrap_tree / 'pexpert'),
                        '-I', str(bridge_tree / 'pexpert/arm')]
    target = json.loads((ROOT / 'note10/target.json').read_text())
    meta = ROOT / target['research_directory'] / 'generated-headers-vmapple/RELEASE_ARM64_VMAPPLE/pexpert/RELEASE/meta_features.h'
    for shift in (12, 14):
        inputs = dict(values); inputs['N10_KERNEL_PAGE_SHIFT'] = shift
        defines = ['-D' + k + '=' + str(v) for k, v in inputs.items()]
        for name in ('pe_note10_bootstrap.c', 'pe_note10_irq.c'):
            source_file = ROOT / 'note10/xnu26' / name
            obj = private / (name + '.synthetic-' + str(shift) + '.o')
            command = [str(compiler), *component_prefix, *component_flags, '-DARM64_BOARD_CONFIG_EXYNOS9825',
                       '-DPEXPERT_KERNEL_PRIVATE', '-include', str(meta), *defines,
                       '-O2', '-mstrict-align', '-mno-implicit-float', '-fno-stack-protector',
                       '-Wall', '-Wextra', '-Werror', '-c', str(source_file), '-o', str(obj)]
            result = subprocess.run(command, capture_output=True, timeout=60)
            log = obj.with_suffix('.log'); log.write_bytes(result.stdout + result.stderr)
            passed = result.returncode == 0
            disassembly = ''
            if passed:
                disassembly = subprocess.check_output([str(compiler.parent / 'llvm-objdump.exe'),
                    '--disassemble', '--no-show-raw-insn', str(obj)]).decode()
                instructions = re.findall(r'^\s*[0-9a-f]+:\s+([a-z].*)$', disassembly, re.MULTILINE)
                if not instructions:
                    raise ValueError('No component instructions disassembled')
                if any(re.search(r'\b(?:v|q|d|s|h|b)\d+\b', line.split('<')[0]) for line in instructions):
                    raise ValueError('Unexpected vector/FP register in kernel component')
                obj.with_suffix('.asm').write_text(disassembly, encoding='utf-8')
            objects.append({'source': name, 'synthetic_page_shift': shift, 'passed': passed,
                            'source_sha256': hashlib.sha256(source_file.read_bytes()).hexdigest(),
                            'object_sha256': hashlib.sha256(obj.read_bytes()).hexdigest() if passed else None,
                            'vector_fp_registers_absent': passed,
                            'command': command, 'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
            if not passed:print(result.stderr.decode('utf-8', errors='replace'))
    report = {'source_commit': reference['commit'], 'patch_sha256': manifest['patch_sha256'],
              'bridge_patch_sha256': bridge_manifest['patch_sha256'],
              'bootstrap_patch_sha256': bootstrap_manifest['patch_sha256'], 'component_objects': objects,
              'cases': results, 'synthetic_positive_inputs': values,
              'hardware_values_verified': False, 'whole_kernel_build': False,
              'foreign_generated_config': 'RELEASE_ARM64_VMAPPLE',
              'limits': 'Actual patched headers with synthetic cache/page inputs and foreign generated configuration. '
                        'No physical board profile or whole XNU build.'}
    (private / 'test-result.json').write_text(json.dumps(report, indent=2))
    passed = all(r['passed'] for r in results + objects)
    print(json.dumps({'header_cases': len(results), 'component_objects': len(objects), 'passed': passed, 'hardware_values_verified': False}))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
