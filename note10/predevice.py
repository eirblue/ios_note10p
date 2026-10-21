"""PC-only component verification. Exit 2 means verified components, deployment blocked.

This runner has no phone transport, unlock, reboot, image installation or flashing step.
Passing component checks must never be interpreted as a bootable kernel.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import os
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'note10/private/predevice'
sys.path.insert(0, str(ROOT / 'note10/compat'))
from active_inputs import userland_reports


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inventory():
    """Bind this run to small reviewable inputs, excluding generated/private data."""
    result = {p.relative_to(ROOT).as_posix(): digest(p)
            for p in sorted((ROOT / 'note10').rglob('*'))
            if p.is_file() and not {'private', '__pycache__'}.intersection(p.relative_to(ROOT / 'note10').parts)
            and (p.suffix.lower() in {'.py', '.ps1', '.c', '.h', '.s', '.ld', '.json', '.patch', '.md'}
                 or p == ROOT / 'note10/xnu26/patches/series')}
    workflow = ROOT / '.github/workflows/note10-native-compile.yml'
    if workflow.is_file():result[workflow.relative_to(ROOT).as_posix()] = digest(workflow)
    return result


def run_step(name, command):
    print(name, flush=True)
    log = OUT / (name + '.log')
    # Every executable/argument is selected below; no shell or user command input.
    with log.open('w', encoding='utf-8') as stream:
        try:
            env = dict(os.environ)
            packages = ROOT / 'host-tools/python-native-packages'
            if packages.is_dir():
                env['PYTHONPATH'] = str(packages) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                    timeout=180, check=False, env=env)
            code = result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            stream.write(str(exc)); code = -1
    return {'name': name, 'passed': code == 0, 'exit_code': code,
            'log': log.relative_to(ROOT).as_posix(), 'log_sha256': digest(log)}


def main():
    if sys.flags.optimize:
        raise SystemExit('Run without -O: component tests use assertions')
    if sys.argv[1:]:
        raise SystemExit('No options accepted; this runner never permits device operations')
    OUT.mkdir(parents=True, exist_ok=True)
    target = json.loads((ROOT / 'note10/target.json').read_text())
    before = inventory()
    steps = []
    inputs = {}
    try:
        # Resolve locally and constrain paths before reading large original inputs.
        ipsw = (ROOT / target['ipsw']).resolve()
        research = (ROOT / target['research_directory']).resolve()
        if not ipsw.is_relative_to(ROOT) or not research.is_relative_to(ROOT):
            raise ValueError('Target path escapes repository')
        print('active-inputs (IPSW SHA256)', flush=True)
        actual = digest(ipsw)
        if actual != target['sha256']:
            raise ValueError('Active IPSW SHA256 mismatch')
        reference = json.loads((research / 'xnu-reference.json').read_text())
        if (reference['commit'], reference['tag']) != (target['public_reference_commit'], target['public_reference_tag']):
            raise ValueError('Public reference does not match active target configuration')
        reports = userland_reports()
        inputs = {'ipsw_sha256': actual, 'userland_files': len(reports),
                  'reference_commit': reference['commit'], 'exact_source_match': reference['exact_match']}
        steps.append({'name': 'active-inputs', 'passed': True})
    except (OSError, ValueError, KeyError) as exc:
        steps.append({'name': 'active-inputs', 'passed': False, 'error': str(exc)})

    if all(s['passed'] for s in steps):
        py = sys.executable
        ps = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File']
        commands = [
            ('compat-objects', [*ps, 'note10/compat/build.ps1']),
            ('gic-objects', [*ps, 'note10/platform/build.ps1']),
            ('capability-elf', [*ps, 'note10/shim/build.ps1']),
            ('capability-synthetic', [py, 'note10/shim/test_cap_entry.py']),
            ('selection', [py, 'note10/xnu26/prepare_build_selection.py']),
            ('timer', [py, 'note10/xnu26/prepare_timer_selection.py']),
            ('bridge-patch', [py, 'note10/xnu26/prepare_irq_bridge.py']),
            ('bridge-synthetic', [py, 'note10/xnu26/test_irq_bridge.py']),
            ('bootstrap-patch', [py, 'note10/xnu26/prepare_irq_bootstrap.py']),
            ('bootstrap-synthetic', [py, 'note10/xnu26/test_irq_bootstrap.py']),
            ('bootstrap-integrated', [py, 'note10/xnu26/test_irq_bootstrap.py', '--integrated']),
            ('board-patch', [py, 'note10/xnu26/prepare_board_profile.py']),
            ('board-synthetic', [py, 'note10/xnu26/test_board_profile.py']),
            ('master-patch', [py, 'note10/xnu26/prepare_master_profile.py']),
            ('master-link-selection', [py, 'note10/xnu26/test_master_profile.py']),
            ('exception-header-patch', [py, 'note10/xnu26/prepare_exception_headers.py']),
            ('architecture-patch', [py, 'note10/xnu26/prepare_architecture_sources.py']),
            ('native-interfaces-patch', [py, 'note10/xnu26/prepare_native_interfaces.py']),
            ('patch-series', [py, 'note10/xnu26/validate_series.py']),
            ('header-dependency-probe', [py, 'note10/xnu26/probe_kernel_headers.py']),
            ('host-config-build', [py, 'note10/xnu26/build_windows_config.py']),
            ('native-configure', [py, 'note10/xnu26/configure_windows_xnu.py']),
            ('native-header-exports', [py, 'note10/xnu26/export_source_headers.py']),
            ('native-selected-c', [py, 'note10/xnu26/compile_native_components.py']),
            ('native-state', [py, 'note10/xnu26/verify_native_state.py']),
            ('cloud-recipe', [py, 'note10/xnu26/test_cloud_recipe.py']),
        ]
        for name, command in commands:
            result = run_step(name, command); steps.append(result)
            if not result['passed']:
                break  # Never let stale dependent outputs count as a successful run.

    after = inventory()
    # Patch generators are expected to reproduce the checked-in patch bytes exactly.
    steps.append({'name': 'reviewable-inputs-unchanged', 'passed': before == after})
    blockers = [
        {'id': 'kernel-build', 'state': 'missing',
         'detail': 'Native config/headers and selected C objects exist. Apple compiler builtins are available in the designated macOS CI. Complete selected generated inputs, hardware platform archive and whole Exynos kernel link remain incomplete; local Windows checks do not establish remote kernel completion.'},
        {'id': 'boot-memory-contract', 'state': 'unverified',
         'detail': 'Entry EL, load/reserved RAM, MMU/cache/granule capabilities and diagnostic recovery are unknown.'},
        {'id': 'gic-handoff', 'state': 'missing',
         'detail': 'No actual handoff producer or cold GIC initialization; priority/security/trigger ownership unverified.'},
        {'id': 'ios-userland', 'state': 'missing',
         'detail': 'PAC/BRK and fixup parts are not integrated with XNU process keys, traps, loader or Apple userland ABI.'},
        {'id': 'device-drivers', 'state': 'missing',
         'detail': 'Storage/APFS boot path, framebuffer, touch and other Exynos device drivers are not integrated.'},
        {'id': 'boot-artifact', 'state': 'missing',
         'detail': 'No linked kernel, Note10 boot image, verified packaging or recovery procedure.'},
        {'id': 'source-abi', 'state': 'unverified',
         'detail': 'Public XNU 12377.121.6 differs from IPSW 12377.122.8; ABI compatibility is unproven.'},
    ]
    report = {'schema': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'PC component verification only', 'target': target, 'inputs': inputs,
              'checks': steps, 'component_checks_passed': all(s['passed'] for s in steps),
              'deployment_ready': False, 'device_operations': [], 'blockers': blockers,
              'source_sha256': after}
    native = ROOT / 'note10/private/windows-xnu/state-result.json'
    if native.is_file() and any(s['name'] == 'native-state' and s['passed'] for s in steps):
        report['native_status'] = json.loads(native.read_text())
    (OUT / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'component_checks_passed': report['component_checks_passed'],
                      'deployment_ready': False, 'blockers': len(blockers),
                      'report': 'note10/private/predevice/report.json'}))
    return 2 if report['component_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
