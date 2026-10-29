"""Exercise v47 source/config binding and its fail-closed mutations."""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from ehld_running_lock_binding import (
    KCONFIG, NATIVE_MODEL, PACKAGE_SOURCES, PREPARED, SOURCES, TARGET,
    assert_scope, package_scope,
)

CASES = (
    'enabled-valid', 'missing-running-flag', 'null-running-flag', 'flag-string', 'version-bool',
    'version-string', 'missing-version', 'wrong-version', 'missing-old-lock',
    'old-lock-version-bool', 'missing-irqsave', 'irqsave-version-bool',
    'missing-config-hash', 'null-config-hash', 'wrong-config-hash',
    'wrong-config-option', 'duplicate-config-option', 'changed-snapshot-file',
    'snapshot-map-mutation', 'missing-source-map', 'mutated-source-map',
    'stray-disabled-version', 'disabled-stray-proof', 'disabled-stray-output',
    'off-old-ehld-enabled-missing-hash', 'off-old-ehld-disabled-missing-hash',
    'off-null-version-missing-hash',
)
PACKAGE_SCOPE_CASES = (
    'on-valid', 'off-absent', 'off-false-old-on', 'off-false-old-off', 'off-null-version',
    'null-flag', 'flag-string', 'flag-integer', 'version-bool', 'version-string',
    'missing-old-lock', 'old-lock-version-bool', 'missing-irqsave',
    'irqsave-version-bool', 'stray-off-version', 'old-version-stray', 'off-stray-proof',
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _copy_fixture(source, destination, off=False):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True)
    for name in ('build-result.json', 'handoff.config'):
        src = source / name
        if src.is_symlink() or not src.is_file():
            raise ValueError('unsafe fixture input: ' + name)
        shutil.copyfile(src, destination / name)
    build = json.loads((destination / 'build-result.json').read_text(encoding='utf8'))
    roots = ['ehld-lock-prepared', 'ehld-irqsave-prepared']
    if not off:
        roots.extend((PREPARED, NATIVE_MODEL))
    for name in roots:
        src = source / name
        if src.is_symlink() or not src.is_dir() or any(p.is_symlink() for p in src.rglob('*')):
            raise ValueError('unsafe v47 binding fixture tree: ' + name)
        shutil.copytree(src, destination / name)
    return build


def _package_cases():
    valid = {'ehld_running_lock_audit': True, 'ehld_running_lock_audit_version': 1,
             'ehld_lock_audit': True, 'ehld_lock_audit_version': 1,
             'ehld_irqsave_audit': True, 'ehld_irqsave_audit_version': 1}
    off_on = {'ehld_running_lock_audit': False, 'ehld_lock_audit': True,
              'ehld_lock_audit_version': 1, 'ehld_irqsave_audit': True,
              'ehld_irqsave_audit_version': 1}
    off_off = {'ehld_running_lock_audit': False, 'ehld_lock_audit': False,
               'ehld_irqsave_audit': False}
    bad = (
        {'ehld_running_lock_audit': None}, {'ehld_running_lock_audit': 'true'}, {'ehld_running_lock_audit': 1},
        {**valid, 'ehld_running_lock_audit_version': True},
        {**valid, 'ehld_running_lock_audit_version': '1'},
        {'ehld_running_lock_audit': True, 'ehld_running_lock_audit_version': 1,
         'ehld_irqsave_audit': True, 'ehld_irqsave_audit_version': 1},
        {**valid, 'ehld_lock_audit_version': True},
        {'ehld_running_lock_audit': True, 'ehld_running_lock_audit_version': 1,
         'ehld_lock_audit': True, 'ehld_lock_audit_version': 1},
        {**valid, 'ehld_irqsave_audit_version': True},
        {'ehld_running_lock_audit': False, 'ehld_running_lock_audit_version': 1},
        {**off_on, 'ehld_lock_audit_version': 2},
        {'ehld_running_lock_audit': False, 'ehld_running_lock_model_sha256': '0' * 64},
    )
    items = [(PACKAGE_SCOPE_CASES[0], valid, True),
             (PACKAGE_SCOPE_CASES[1], {}, False),
             (PACKAGE_SCOPE_CASES[2], off_on, False),
             (PACKAGE_SCOPE_CASES[3], off_off, False),
             (PACKAGE_SCOPE_CASES[4], {'ehld_running_lock_audit': False, 'ehld_running_lock_audit_version': None}, False)]
    items.extend((PACKAGE_SCOPE_CASES[i + 5], item, None) for i, item in enumerate(bad))
    result = []
    for name, metadata, expected in items:
        try:
            value = package_scope(metadata)
            accepted = True
        except (ValueError, TypeError, KeyError):
            value, accepted = None, False
        if expected is None:
            if accepted:
                raise AssertionError('package_scope accepted malformed case: ' + name)
        elif not accepted or type(value) is not bool or value is not expected:
            raise AssertionError('package_scope result differs: ' + name)
        result.append({'case': name, 'accepted': accepted, 'scope': value})
    return result


def run(artifact, output):
    artifact, output = Path(artifact), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    generated, logs = {}, {}
    package_scope_results = _package_cases()
    for name in CASES:
        with tempfile.TemporaryDirectory(dir=output) as temp:
            root = Path(temp) / 'fixture'
            build = _copy_fixture(artifact, root, off=name.startswith('off-'))
            config = root / 'handoff.config'
            accepted_expected = name in ('enabled-valid', 'off-old-ehld-enabled-missing-hash', 'off-old-ehld-disabled-missing-hash', 'off-null-version-missing-hash')
            if name == 'missing-running-flag': build.pop('ehld_running_lock_audit')
            elif name == 'null-running-flag': build['ehld_running_lock_audit'] = None
            elif name == 'flag-string': build['ehld_running_lock_audit'] = 'true'
            elif name == 'version-bool': build['ehld_running_lock_audit_version'] = True
            elif name == 'version-string': build['ehld_running_lock_audit_version'] = '1'
            elif name == 'missing-version': build.pop('ehld_running_lock_audit_version')
            elif name == 'wrong-version': build['ehld_running_lock_audit_version'] = 2
            elif name == 'missing-old-lock': build['ehld_lock_audit'] = False
            elif name == 'old-lock-version-bool': build['ehld_lock_audit_version'] = True
            elif name == 'missing-irqsave': build['ehld_irqsave_audit'] = False
            elif name == 'irqsave-version-bool': build['ehld_irqsave_audit_version'] = True
            elif name == 'missing-config-hash': build.pop('effective_config_sha256')
            elif name == 'null-config-hash': build['effective_config_sha256'] = None
            elif name == 'wrong-config-hash': build['effective_config_sha256'] = '0' * 64
            elif name == 'wrong-config-option':
                raw = config.read_bytes().replace(b'CONFIG_NOTE10_EHLD_RUNNING_LOCK_AUDIT=y',
                                                  b'# CONFIG_NOTE10_EHLD_RUNNING_LOCK_AUDIT is not set')
                config.write_bytes(raw); build['effective_config_sha256'] = sha(raw)
            elif name == 'duplicate-config-option':
                raw = config.read_bytes() + b'CONFIG_NOTE10_EHLD_RUNNING_LOCK_AUDIT=y\n'
                config.write_bytes(raw); build['effective_config_sha256'] = sha(raw)
            elif name == 'changed-snapshot-file':
                target = root / PREPARED / TARGET
                target.write_bytes(target.read_bytes() + b'\n')
            elif name == 'snapshot-map-mutation':
                build['ehld_running_lock_snapshot_sha256'][TARGET] = '0' * 64
            elif name == 'missing-source-map': build.pop('ehld_running_lock_sources_sha256')
            elif name == 'mutated-source-map':
                build['ehld_running_lock_sources_sha256'][SOURCES[0]] = '0' * 64
            elif name == 'stray-disabled-version':
                build['ehld_running_lock_audit'] = False
                build['ehld_running_lock_audit_version'] = 1
            elif name == 'disabled-stray-proof':
                for root_name in (PREPARED, NATIVE_MODEL):
                    shutil.rmtree(root / root_name)
                build = {key: value for key, value in build.items()
                         if not key.startswith('ehld_running_lock_') or key in ('ehld_running_lock_audit', 'ehld_running_lock_model_sha256')}
                build['ehld_running_lock_audit'] = False
                build['ehld_running_lock_model_sha256'] = '0' * 64
            elif name == 'disabled-stray-output':
                build = {key: value for key, value in build.items()
                         if not key.startswith('ehld_running_lock_') or key == 'ehld_running_lock_audit'}
                build['ehld_running_lock_audit'] = False
                (root / PREPARED).rename(root / 'ehld-running-lock-stray')
            elif name.startswith('off-'):
                build = {key: value for key, value in build.items()
                         if not key.startswith('ehld_running_lock_') or key == 'ehld_running_lock_audit'}
                if name.endswith('enabled-missing-hash'):
                    build['ehld_running_lock_audit'] = False
                    build.pop('ehld_running_lock_audit_version', None)
                    build.pop('effective_config_sha256', None)
                    raw = config.read_bytes().replace(b'CONFIG_NOTE10_EHLD_RUNNING_LOCK_AUDIT=y\n', b'')
                    config.write_bytes(raw)
                elif name.endswith('disabled-missing-hash'):
                    build['ehld_running_lock_audit'] = False
                    build.pop('ehld_running_lock_audit_version', None)
                    build.pop('ehld_lock_audit', None)
                    build.pop('ehld_lock_audit_version', None)
                    build.pop('ehld_irqsave_audit', None)
                    build.pop('ehld_irqsave_audit_version', None)
                    build.pop('effective_config_sha256', None)
                    raw = config.read_bytes().replace(b'CONFIG_NOTE10_EHLD_RUNNING_LOCK_AUDIT=y\n', b'')
                    config.write_bytes(raw)
                elif name.endswith('null-version-missing-hash'):
                    build['ehld_running_lock_audit'] = False
                    build['ehld_running_lock_audit_version'] = None
                    build.pop('effective_config_sha256', None)
                    raw = config.read_bytes().replace(b'CONFIG_NOTE10_EHLD_RUNNING_LOCK_AUDIT=y\n', b'')
                    config.write_bytes(raw)
            try:
                value = assert_scope(root, build)
                accepted = True
            except (ValueError, TypeError, KeyError, FileNotFoundError):
                value, accepted = None, False
            if accepted is not accepted_expected or (accepted and type(value) is not bool):
                raise AssertionError('assert_scope case differs: ' + name)
            if name == 'enabled-valid' and value is not True:
                raise AssertionError('enabled source/config scope did not validate')
            if name.startswith('off-') and value is not False:
                raise AssertionError('valid default-off scope did not return exact False')
            result = {'case': name, 'accepted': accepted, 'scope': value}
            cases.append(result)
            case_file = output / (name + '.py')
            log_file = output / (name + '.log')
            case_file.write_text(json.dumps({'case': name, 'build': build, 'config_sha256': sha(config.read_bytes())}, sort_keys=True),
                                 encoding='utf8', newline='\n')
            log_file.write_text(('PASS ' if accepted else 'REJECT ') + name + '\n', encoding='utf8', newline='\n')
            generated[name], logs[name] = sha(case_file.read_bytes()), sha(log_file.read_bytes())
    proof = {
        'schema_version': 1, 'passed': True, 'hardware_verified': False,
        'cases': list(CASES), 'case_results': cases,
        'package_scope_cases': list(PACKAGE_SCOPE_CASES), 'package_scope_results': package_scope_results,
        'generated_sha256': generated, 'logs_sha256': logs,
        'source_map_sha256': sha((Path(__file__).resolve().parent / 'ehld_running_lock_binding.py').read_bytes()),
        'harness_sha256': sha(Path(__file__).read_bytes()),
    }
    (output / 'result.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf8', newline='\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.artifact, args.output), sort_keys=True))
