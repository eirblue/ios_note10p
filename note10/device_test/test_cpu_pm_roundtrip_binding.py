"""Focused strict scope/source mutation checks for v49."""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from cpu_pm_roundtrip_binding import PREFIX, assert_scope, package_scope

CASES = (
    'enabled-valid', 'missing-flag', 'null-flag', 'flag-string', 'version-bool',
    'version-string', 'missing-version', 'wrong-version', 'missing-config-hash',
    'null-config-hash', 'wrong-config-hash', 'wrong-config-option',
    'duplicate-config-option', 'snapshot-map-mutation', 'missing-source-map',
    'mutated-source-map', 'off-minimal', 'off-stray-version',
    'off-stray-proof', 'off-stray-output',
)
PACKAGE_SCOPE_CASES = (
    'on-valid', 'off-absent-prior-on', 'off-absent-prior-off', 'off-false-prior-on',
    'off-false-prior-off', 'off-null-version', 'null-flag', 'flag-string',
    'flag-int', 'version-bool', 'version-string', 'missing-prior', 'prior-not-on',
    'off-stray-proof',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def package_cases():
    prior = {'ehld_lock_audit': True, 'ehld_lock_audit_version': 1,
             'ehld_irqsave_audit': True, 'ehld_irqsave_audit_version': 1,
             'ehld_running_lock_audit': True, 'ehld_running_lock_audit_version': 2, 'auto_return_diagnostic': True}
    cases = [
        ('on-valid', {'cpu_pm_roundtrip': True, 'cpu_pm_roundtrip_version': 1, **prior}, True),
        ('off-absent-prior-on', prior, False),
        ('off-absent-prior-off', {}, False),
        ('off-false-prior-on', {'cpu_pm_roundtrip': False, **prior}, False),
        ('off-false-prior-off', {'cpu_pm_roundtrip': False}, False),
        ('off-null-version', {'cpu_pm_roundtrip': False, 'cpu_pm_roundtrip_version': None}, False),
        ('null-flag', {'cpu_pm_roundtrip': None}, None),
        ('flag-string', {'cpu_pm_roundtrip': 'true'}, None),
        ('flag-int', {'cpu_pm_roundtrip': 1}, None),
        ('version-bool', {'cpu_pm_roundtrip': True, 'cpu_pm_roundtrip_version': True, **prior}, None),
        ('version-string', {'cpu_pm_roundtrip': True, 'cpu_pm_roundtrip_version': '1', **prior}, None),
        ('missing-prior', {'cpu_pm_roundtrip': True, 'cpu_pm_roundtrip_version': 1}, None),
        ('prior-not-on', {'cpu_pm_roundtrip': True, 'cpu_pm_roundtrip_version': 1, **{**prior, 'ehld_running_lock_audit': False}}, None),
        ('off-stray-proof', {'cpu_pm_roundtrip': False, 'cpu_pm_roundtrip_model_sha256': '0'*64}, None),
    ]
    result = []
    for name, metadata, expected in cases:
        try:
            value = package_scope(metadata)
            accepted = True
        except (ValueError, TypeError, KeyError):
            value, accepted = None, False
        if expected is None and accepted:
            raise AssertionError('package_scope accepted ' + name)
        if expected is not None and (not accepted or type(value) is not bool or value is not expected):
            raise AssertionError('package_scope outcome differs: ' + name)
        result.append({'case': name, 'accepted': accepted, 'scope': value})
    return result


def run(artifact, output):
    artifact, output = Path(artifact), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    build = json.loads((artifact / 'build-result.json').read_text(encoding='utf8'))
    scope_results = package_cases()
    outcomes = []
    generated, logs = {}, {}
    for name in CASES:
        expected = name in ('enabled-valid', 'off-minimal')
        value = None
        if name == 'enabled-valid':
            value = assert_scope(artifact, dict(build))
            accepted = True
        elif name.startswith('off-'):
            with tempfile.TemporaryDirectory(dir=output) as temp:
                root = Path(temp) / 'fixture'
                root.mkdir()
                config = (artifact / 'handoff.config').read_bytes()
                config = config.replace(b'CONFIG_NOTE10_CPU_PM_ROUNDTRIP=y\n', b'')
                (root / 'handoff.config').write_bytes(config)
                (root / 'Image').write_bytes(b'')
                off = {k: v for k, v in build.items() if not k.startswith(PREFIX)}
                off['cpu_pm_roundtrip'] = False
                off.pop('effective_config_sha256', None)
                if name == 'off-stray-version':
                    off['cpu_pm_roundtrip_version'] = 1
                if name == 'off-stray-proof':
                    off['cpu_pm_roundtrip_model_sha256'] = '0' * 64
                if name == 'off-stray-output':
                    (root / 'Image').write_bytes(b'')
                    (root / 'cpu-pm-roundtrip-model').mkdir()
                try:
                    value = assert_scope(root, off)
                    accepted = True
                except (ValueError, TypeError, KeyError):
                    accepted = False
        else:
            changed = dict(build)
            raw = (artifact / 'handoff.config').read_bytes()
            if name == 'missing-flag': changed.pop('cpu_pm_roundtrip', None)
            elif name == 'null-flag': changed['cpu_pm_roundtrip'] = None
            elif name == 'flag-string': changed['cpu_pm_roundtrip'] = 'true'
            elif name == 'version-bool': changed['cpu_pm_roundtrip_version'] = True
            elif name == 'version-string': changed['cpu_pm_roundtrip_version'] = '1'
            elif name == 'missing-version': changed.pop('cpu_pm_roundtrip_version', None)
            elif name == 'wrong-version': changed['cpu_pm_roundtrip_version'] = 2
            elif name == 'missing-config-hash': changed.pop('effective_config_sha256', None)
            elif name == 'null-config-hash': changed['effective_config_sha256'] = None
            elif name == 'wrong-config-hash': changed['effective_config_sha256'] = '0' * 64
            elif name in ('wrong-config-option', 'duplicate-config-option'):
                bad = raw.replace(b'CONFIG_NOTE10_CPU_PM_ROUNDTRIP=y', b'# CONFIG_NOTE10_CPU_PM_ROUNDTRIP is not set') if name == 'wrong-config-option' else raw + b'CONFIG_NOTE10_CPU_PM_ROUNDTRIP=y\n'
                changed['effective_config_sha256'] = sha(bad)
                with tempfile.TemporaryDirectory(dir=output) as temp:
                    root = Path(temp) / 'fixture'; root.mkdir(); (root / 'handoff.config').write_bytes(bad)
                    try: assert_scope(root, changed); accepted = True
                    except (ValueError, TypeError, KeyError): accepted = False
            elif name == 'snapshot-map-mutation':
                changed['cpu_pm_roundtrip_snapshot_sha256'] = dict(changed['cpu_pm_roundtrip_snapshot_sha256'])
                first = next(iter(changed['cpu_pm_roundtrip_snapshot_sha256']))
                changed['cpu_pm_roundtrip_snapshot_sha256'][first] = '0' * 64
            elif name == 'missing-source-map': changed.pop('cpu_pm_roundtrip_sources_sha256')
            elif name == 'mutated-source-map':
                changed['cpu_pm_roundtrip_sources_sha256'] = dict(changed['cpu_pm_roundtrip_sources_sha256'])
                first = next(iter(changed['cpu_pm_roundtrip_sources_sha256']))
                changed['cpu_pm_roundtrip_sources_sha256'][first] = '0' * 64
            if name not in ('wrong-config-option', 'duplicate-config-option'):
                try: value = assert_scope(artifact, changed); accepted = True
                except (ValueError, TypeError, KeyError, FileNotFoundError): accepted = False
        if accepted is not expected:
            raise AssertionError('assert_scope outcome differs: ' + name)
        outcomes.append({'case': name, 'accepted': accepted, 'scope': value if name in ('enabled-valid', 'off-minimal') else None})
        code = output / (name + '.py'); log = output / (name + '.log')
        code.write_text(json.dumps({'case': name, 'expected_accept': expected}, sort_keys=True) + '\n', encoding='utf8', newline='\n')
        log.write_text(('PASS ' if accepted else 'REJECT ') + name + '\n', encoding='utf8', newline='\n')
        generated[name], logs[name] = sha(code.read_bytes()), sha(log.read_bytes())
    proof = {'schema_version': 1, 'passed': True, 'hardware_verified': False,
             'cases': list(CASES), 'case_results': outcomes,
             'package_scope_cases': list(PACKAGE_SCOPE_CASES), 'package_scope_results': scope_results,
             'generated_sha256': generated, 'logs_sha256': logs,
             'binding_sha256': sha((Path(__file__).resolve().parent / 'cpu_pm_roundtrip_binding.py').read_bytes()),
             'harness_sha256': sha(Path(__file__).read_bytes())}
    (output / 'result.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf8', newline='\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--artifact', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(run(args.artifact, args.output), sort_keys=True))
