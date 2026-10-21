"""Exercise pinned doconf sed/awk text selection and actual GNU Make link fragments."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from prepare_build_selection import ROOT, NDK
from prepare_master_profile import SOC, REL

DOCONF_PIN = 'e56adddb1011213afd1328a782a5df517f1a42a2e9bc8aadd8ffa7220b3550e6'
GLOBAL_PIN = '13e798255556e07e07b438a9e71a559c34e2bc35c5602655319a6c28fc6e9845'


def main():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    reference = json.loads((ROOT / target['research_directory'] / 'xnu-reference.json').read_text())
    source = ROOT / reference['source_directory']
    private = ROOT / 'note10/private/xnu26-master'
    tree = private / 'patched-inputs'
    manifest = json.loads((private / 'patch-result.json').read_text())
    for name, expected in manifest['files'].items():
        if hashlib.sha256((tree / name).read_bytes()).hexdigest() != expected:
            raise ValueError('MASTER patch input changed')
    doconf = (source / 'SETUP/config/doconf').read_bytes()
    global_master = (source / 'config/MASTER').read_bytes()
    if hashlib.sha256(doconf).hexdigest() != DOCONF_PIN or hashlib.sha256(global_master).hexdigest() != GLOBAL_PIN:
        raise ValueError('Pinned configuration selector changed')
    text = doconf.decode()
    # Execute just the unchanged upstream text-selection pipeline, not csh's
    # filesystem mutation/config-tool stages. The SoC file has no CPP directives.
    start = text.index('    sed -n \\\n')
    end = text.index("' >$SYSCONF.new", start) + 1
    pipeline = text[start:end]
    script = 'export PATH=/usr/bin:/bin\n' + pipeline
    (private / 'upstream-selector.sh').write_text(script, newline='\n')
    soc = (tree / SOC).read_bytes()
    if re.search(rb'^#(?:if|else|elif|endif)\b', global_master + soc, re.MULTILINE):
        raise ValueError('Cannot skip unifdef on conditional input')
    selector_line = 'foreach master_file (${MASTER}.${cpu}.${SOC_CONFIG}.${PLATFORM} ${MASTER}.${cpu}.${SOC_CONFIG} ${MASTER}.${cpu}.${PLATFORM} ${MASTER}.${cpu})'
    if selector_line not in text:
        raise ValueError('Upstream MASTER precedence changed')
    candidates = ['config/MASTER.arm64.exynos9825.iPhoneOS', SOC,
                  'config/MASTER.arm64.iPhoneOS', 'config/MASTER.arm64']
    selected = next(n for n in candidates if (tree / n).is_file() or (source / n).is_file())
    if selected != SOC:
        raise ValueError('SoC profile is not selected')
    configs = []
    bash = Path(r'C:/Program Files/Git/bin/bash.exe')
    for variant in ('RELEASE', 'DEVELOPMENT', 'DEBUG'):
        data = global_master + soc + ('\n+' + variant + '\n').encode() + global_master + soc
        result = subprocess.run([str(bash), '--noprofile', '--norc', '-c', script], input=data,
                                capture_output=True, timeout=30, check=True)
        output = result.stdout.decode()
        path = private / ('config.' + variant + '_ARM64')
        path.write_bytes(result.stdout)
        options = dict((name, value or '1') for name, value in
                       re.findall(r'^options\s+([A-Z0-9_]+)(?:=([^\s#]+))?', output, re.MULTILINE))
        forbidden = {'CONFIG_PMAP_PPL', 'CONFIG_SPTM', 'CONFIG_EXCLAVES', 'CONFIG_CPU_COUNTERS',
                     'CONFIG_PERVASIVE_CPI', 'CONFIG_PERVASIVE_ENERGY', 'CONFIG_PV_TICKET'}
        if forbidden.intersection(options) or not {'MACH', 'MACH_BSD', 'CONFIG_MACF', 'CONFIG_KERNEL_INTEGRITY'}.issubset(options):
            raise ValueError('Unexpected MASTER option selection: ' + variant)
        if re.search(r'^pseudo-device\s+monotonic\b', output, re.MULTILINE):
            raise ValueError('Apple CPU counter pseudo-device still selected')
        if variant == 'RELEASE' and options.get('MACH_ASSERT'):
            raise ValueError('Release unexpectedly has assertions')
        if variant != 'RELEASE' and options.get('MACH_ASSERT') != '1':
            raise ValueError('Development/debug assertions missing')
        configs.append({'variant': variant, 'selected': selected, 'options': options,
                        'text_sha256': hashlib.sha256(result.stdout).hexdigest(), 'passed': True})

    new_def = (tree / REL).read_text(encoding='utf-8')
    fragment = manifest['link_fragment']
    if fragment not in new_def:
        raise ValueError('Link test fragment differs from patch')
    makefile = private / 'link.mk'
    makefile.write_text(fragment + '\n$(info flags=$(LDFLAGS_KERNEL_ONLY))\nall: ;\n', newline='\n')
    # A real component object archive is a fixture for path checks only. It is
    # never passed off as the complete Note10 platform support implementation.
    fixture = private / 'link-fixture.a'
    obj = ROOT / 'note10/private/xnu26-board/pe_note10_irq.c.synthetic-14.o'
    tools = NDK / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    subprocess.run([str(tools / 'llvm-ar.exe'), 'rcs', str(fixture), str(obj)], check=True)
    archive = fixture.relative_to(ROOT).as_posix()
    defaults = {'CURRENT_MACHINE_CONFIG': 'EXYNOS9825', 'PLATFORM': 'iPhoneOS',
                'CURRENT_KERNEL_CONFIG': 'DEVELOPMENT', 'KDKROOT': 'synthetic-kdk',
                'N10_PLATFORM_ARCHIVE': archive}
    tests = [(name.lower(), {'CURRENT_KERNEL_CONFIG': name}, None) for name in ('RELEASE', 'DEVELOPMENT', 'DEBUG')]
    tests += [('missing_archive', {'N10_PLATFORM_ARCHIVE': ''}, 'requires explicit N10_PLATFORM_ARCHIVE'),
              ('nonexistent_archive', {'N10_PLATFORM_ARCHIVE': 'note10/private/no-such-support.a'}, 'does not exist'),
              ('whitespace', {'N10_PLATFORM_ARCHIVE': 'a b.a'}, 'must not contain whitespace'),
              ('comma', {'N10_PLATFORM_ARCHIVE': 'a,b.a'}, 'must not contain commas'),
              ('suffix', {'N10_PLATFORM_ARCHIVE': 'a.txt'}, 'must have suffix .a'),
              ('wrong_platform', {'PLATFORM': 'MacOSX'}, 'requires PLATFORM=iPhoneOS'),
              ('sptm', {'CURRENT_KERNEL_CONFIG': 'SPTM'}, 'only RELEASE DEVELOPMENT DEBUG'),
              ('kasan', {'CURRENT_KERNEL_CONFIG': 'KASAN'}, 'only RELEASE DEVELOPMENT DEBUG'),
              ('empty_config', {'CURRENT_KERNEL_CONFIG': ''}, 'only RELEASE DEVELOPMENT DEBUG'),
              ('multiple_configs', {'CURRENT_KERNEL_CONFIG': 'RELEASE DEVELOPMENT'}, 'only RELEASE DEVELOPMENT DEBUG'),
              ('partially_valid_config', {'CURRENT_KERNEL_CONFIG': 'DEVELOPMENT BAD'}, 'only RELEASE DEVELOPMENT DEBUG')]
    links = []
    make = NDK / 'prebuilt/windows-x86_64/bin/make.exe'
    for name, override, expected in tests:
        inputs = dict(defaults); inputs.update(override)
        result = subprocess.run([str(make), '--no-print-directory', '-f', str(makefile), 'all',
                                 *[k + '=' + v for k, v in inputs.items()]], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        diagnostics = result.stdout + result.stderr
        passed = (result.returncode == 0 and '-force_load,' + archive in diagnostics and 'KernelSupport' not in diagnostics) \
                 if expected is None else (result.returncode != 0 and expected in diagnostics)
        if not passed:
            raise ValueError(name + ': ' + diagnostics)
        links.append({'name': name, 'passed': passed, 'expected_error': expected})
    for machine in ('T8101', 'VMAPPLE', 'NONE'):
        result = subprocess.run([str(make), '--no-print-directory', '-f', str(makefile), 'all',
                                 'CURRENT_MACHINE_CONFIG=' + machine, 'KDKROOT=synthetic-kdk',
                                 'CURRENT_KERNEL_CONFIG=RELEASE'], cwd=ROOT, capture_output=True, text=True, check=True)
        expected = 'KernelSupport/lib' + machine + '.os.RELEASE.a'
        if (expected in result.stdout) != (machine != 'NONE'):
            raise ValueError('Existing link branch changed')
        links.append({'name': 'preserved_' + machine, 'passed': True})
    report = {'source_commit': reference['commit'], 'patch_sha256': manifest['patch_sha256'],
              'doconf_sha256': DOCONF_PIN, 'global_master_sha256': GLOBAL_PIN,
              'upstream_selector_sha256': hashlib.sha256(script.encode()).hexdigest(),
              'config_texts': configs, 'link_cases': links,
              'fixture_archive_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
              'config_tool_executed': False, 'full_kernel_link': False, 'platform_archive_implemented': False,
              'limits': 'Upstream sed/awk config text selection and GNU Make path/branch checks only. '
                        'No config-generated headers, complete platform archive or whole kernel link.'}
    (private / 'test-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'config_texts': len(configs), 'link_cases': len(links), 'passed': True,
                      'platform_archive_implemented': False}))


if __name__ == '__main__':
    main()
