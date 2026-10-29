"""Strict v47 EHLD running-scalar lock scope and proof binding."""
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from prepare_ehld_running_lock_audit import KCONFIG, OPTION, TARGET, prepare, snapshot, validate_transform

HERE = Path(__file__).resolve().parent
SOURCES = (
    'prepare_ehld_running_lock_audit.py',
    'prepare_ehld_running_lock_flow_compat.py',
    'test_ehld_running_lock_audit.py',
    'ehld_running_lock_binding.py',
    'test_ehld_running_lock_binding.py',
    'test_ehld_running_lock_package_flow.py',
)
PACKAGE_SOURCES = (
    'prepare_linux_boot.py',
    'build_boot_test_packages.py',
    'precheck_window_access.py',
    'stage_phase2.py',
    'collect_reservation.py',
)
NATIVE_MODEL = 'ehld-running-lock-model'
PREPARED = 'ehld-running-lock-prepared'
NATIVE_BINDING_MODEL = 'ehld-running-lock-binding-model'
PACKAGE_FLOW_MODEL = 'ehld-running-lock-package-flow-model'
PREFIX = 'ehld_running_lock_'
FIELDS = (
    'ehld_running_lock_audit_version',
    'ehld_running_lock_baseline_sha256',
    'ehld_running_lock_prepared_sha256',
    'ehld_running_lock_snapshot_sha256',
    'ehld_running_lock_sources_sha256',
    'ehld_running_lock_package_sources_sha256',
    'ehld_running_lock_model_sha256',
    'ehld_running_lock_binding_sha256',
    'ehld_running_lock_package_flow_sha256',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _valid_hash(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _hash_map(value, keys):
    return isinstance(value, dict) and set(value) == set(keys) and all(_valid_hash(v) for v in value.values())


def _file_set(root):
    root = Path(root)
    return {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and not p.is_symlink()}


def package_scope(metadata):
    """Return a strict bool and reject malformed or unsupported downgrade metadata."""
    if not isinstance(metadata, dict):
        raise ValueError('EHLD running-lock metadata must be an object')
    from ehld_irqsave_binding import package_scope as prior_package_scope
    prior_scope = prior_package_scope(metadata)
    if type(prior_scope) is not bool:
        raise ValueError('prior EHLD irqsave package scope malformed')
    flag = metadata.get('ehld_running_lock_audit')
    version = metadata.get('ehld_running_lock_audit_version')
    if 'ehld_running_lock_audit' in metadata and type(flag) is not bool:
        raise ValueError('EHLD running-lock package flag must be bool or absent')
    old_flag = metadata.get('ehld_lock_audit')
    old_version = metadata.get('ehld_lock_audit_version')
    irq_flag = metadata.get('ehld_irqsave_audit')
    irq_version = metadata.get('ehld_irqsave_audit_version')
    for name, value in (('EHLD lock', old_flag), ('EHLD irqsave', irq_flag)):
        if value is not None and type(value) is not bool:
            raise ValueError(name + ' package flag must be bool or absent')
    for name, flag_value, version_value in (
        ('EHLD lock', old_flag, old_version), ('EHLD irqsave', irq_flag, irq_version),
    ):
        if flag_value is True:
            if type(version_value) is not int or version_value != 1:
                raise ValueError(name + ' package dependency/version invalid')
        elif version_value is not None:
            raise ValueError(name + ' package version is stray')
    if flag is True:
        if type(version) is not int or version != 1 or prior_scope is not True:
            raise ValueError('EHLD running-lock dependency/version invalid')
        return True
    if version is not None:
        raise ValueError('EHLD running-lock version is stray')
    stray = [key for key in metadata if key.startswith(PREFIX) and key not in (
        'ehld_running_lock_audit', 'ehld_running_lock_audit_version')
    ]
    if stray:
        raise ValueError('EHLD running-lock package proof is stray while disabled')
    return False


def assert_scope(root, build):
    root = Path(root)
    if not isinstance(build, dict):
        raise ValueError('EHLD running-lock build metadata must be an object')
    flag = build.get('ehld_running_lock_audit')
    if 'ehld_running_lock_audit' in build and type(flag) is not bool:
        raise ValueError('EHLD running-lock flag malformed')
    enabled = flag is True
    config_path = root / 'handoff.config'
    if config_path.is_symlink() or not config_path.is_file():
        raise ValueError('EHLD running-lock config missing or unsafe')
    config = config_path.read_bytes()
    config_lines = config.splitlines()
    entries = [line for line in config_lines if OPTION.encode() in line]
    if enabled:
        if entries != [(OPTION + '=y').encode()]:
            raise ValueError('EHLD running-lock option must be uniquely enabled')
        if b'CONFIG_NOTE10_EHLD_LOCK_AUDIT=y' not in config_lines or b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=y' not in config_lines:
            raise ValueError('EHLD running-lock configuration dependencies missing')
    elif entries not in ([], [(b'# ' + OPTION.encode() + b' is not set')], [(OPTION + '=n').encode()]):
        raise ValueError('EHLD running-lock disabled config malformed or duplicated')
    if 'effective_config_sha256' in build and build.get('effective_config_sha256') != sha(config):
        raise ValueError('EHLD running-lock effective config hash differs')
    if enabled and 'effective_config_sha256' not in build:
        raise ValueError('EHLD running-lock effective config hash missing')
    directories = (PREPARED, NATIVE_MODEL, NATIVE_BINDING_MODEL, PACKAGE_FLOW_MODEL)
    prefixed = [p.name for p in root.iterdir() if p.name.startswith('ehld-running-lock-')]
    if not enabled:
        stray = [key for key in build if key.startswith(PREFIX) and key not in (
            'ehld_running_lock_audit', 'ehld_running_lock_audit_version')]
        if build.get('ehld_running_lock_audit_version') is not None and 'ehld_running_lock_audit_version' in build:
            stray.append('ehld_running_lock_audit_version')
        if stray or any((root / name).exists() for name in directories) or prefixed:
            raise ValueError('disabled EHLD running-lock evidence downgrade')
        # New config may be absent or the single explicit n/not-set representation.
        return False
    if type(build.get('ehld_running_lock_audit_version')) is not int or build['ehld_running_lock_audit_version'] != 1:
        raise ValueError('EHLD running-lock schema version invalid')
    if build.get('ehld_lock_audit') is not True or build.get('ehld_irqsave_audit') is not True:
        raise ValueError('EHLD running-lock opt-in dependencies are disabled')
    if type(build.get('ehld_lock_audit_version')) is not int or build.get('ehld_lock_audit_version') != 1:
        raise ValueError('EHLD lock schema dependency invalid')
    if type(build.get('ehld_irqsave_audit_version')) is not int or build.get('ehld_irqsave_audit_version') != 1:
        raise ValueError('EHLD irqsave schema dependency invalid')
    if not (root / 'ehld-lock-prepared').is_dir() or not (root / 'ehld-irqsave-prepared').is_dir():
        raise ValueError('prior v45/v46 EHLD snapshots missing')
    baseline = build.get('ehld_irqsave_snapshot_sha256')
    if not isinstance(baseline, dict) or len(baseline) != 78 or TARGET not in baseline or KCONFIG not in baseline:
        raise ValueError('exact v46 78-source snapshot map required')
    for name, digest in baseline.items():
        rel = Path(name)
        if rel.is_absolute() or rel.as_posix() != name or '..' in rel.parts or not _valid_hash(digest):
            raise ValueError('invalid v46 snapshot map path or hash')
    baseline_dir = root / 'ehld-irqsave-prepared'
    prepared_dir = root / PREPARED
    if _file_set(baseline_dir) != set(baseline) or _file_set(prepared_dir) != set(baseline):
        raise ValueError('v46/v47 snapshot file sets differ')
    if {name: sha((baseline_dir / name).read_bytes()) for name in baseline} != baseline:
        raise ValueError('v46 snapshot hash mismatch')
    current = build.get('ehld_running_lock_snapshot_sha256')
    if not _hash_map(current, baseline):
        raise ValueError('v47 snapshot map invalid')
    actual = {name: sha((prepared_dir / name).read_bytes()) for name in baseline}
    if actual != current:
        raise ValueError('v47 snapshot file hash mismatch')
    changed = {name for name in baseline if current[name] != baseline[name]}
    if changed != {TARGET, KCONFIG}:
        raise ValueError('v47 snapshot must change exactly EHLD source and Kconfig')
    if build.get('ehld_running_lock_baseline_sha256') != {name: baseline[name] for name in (TARGET, KCONFIG)}:
        raise ValueError('v47 baseline pair differs')
    if build.get('ehld_running_lock_prepared_sha256') != {name: current[name] for name in (TARGET, KCONFIG)}:
        raise ValueError('v47 prepared pair differs')
    validate_transform((baseline_dir / TARGET).read_bytes(), (prepared_dir / TARGET).read_bytes())
    for key, names in (
        ('ehld_running_lock_sources_sha256', SOURCES),
        ('ehld_running_lock_package_sources_sha256', PACKAGE_SOURCES),
    ):
        if not _hash_map(build.get(key), names):
            raise ValueError('v47 source map invalid: ' + key)
        live = {name: sha((HERE / name).read_bytes()) for name in names}
        if build[key] != live:
            raise ValueError('v47 current source map stale: ' + key)
    with tempfile.TemporaryDirectory(dir=root) as temp:
        tmp = Path(temp)
        reconstructed = tmp / 'prepared'
        shutil.copytree(baseline_dir, reconstructed)
        prepare(reconstructed, True, baseline)
        rebuilt = snapshot(reconstructed, tmp / 'snapshot', baseline)
        if rebuilt != current:
            raise ValueError('v47 snapshot is not reproducible from v46')
    if not isinstance(build.get('ehld_running_lock_model_sha256'), str):
        raise ValueError('v47 native model hash missing')
    model = root / NATIVE_MODEL
    if model.is_symlink() or not model.is_dir():
        raise ValueError('v47 native model proof missing')
    raw = (model / 'result.json').read_bytes()
    if sha(raw) != build.get('ehld_running_lock_model_sha256'):
        raise ValueError('v47 native proof digest differs')
    proof = json.loads(raw)
    from test_ehld_running_lock_audit import (
        CASES, RUNTIME_CASES, PRE_GETTER, LOCK_GETTER, extract_functions,
        c_harness, _mutation_rejections,
    )
    if type(proof.get('schema_version')) is not int or proof['schema_version'] != 1:
        raise ValueError('v47 native proof schema invalid')
    if proof.get('passed') is not True or proof.get('hardware_verified') is not False:
        raise ValueError('v47 native proof truth fields invalid')
    if proof.get('cases') != list(CASES) or proof.get('runtime_cases') != list(RUNTIME_CASES) or proof.get('harness_sha256') != sha((HERE / 'test_ehld_running_lock_audit.py').read_bytes()):
        raise ValueError('v47 native proof source/cases stale')
    if proof.get('legacy_path_inventory') != {
        'cpu_pm_online_locked': True, 'cpu_pm_predown_locked': True,
        'prior_getter_unlocked_read_once': True, 'trylock_getter_busy_sentinel_no_event_access': True,
        'updater_main_then_ctrl_locked_running_read': True,
        'cpu_pm_callbacks_invoked': False, 'updater_invoked': False,
        'event_pointer_dereferenced': False,
    }:
        raise ValueError('v47 legacy source inventory differs')
    source_inputs = (TARGET, PRE_GETTER, LOCK_GETTER)
    expected_inputs = {name: sha((prepared_dir / name).read_bytes()) for name in source_inputs}
    if proof.get('source_inputs_sha256') != expected_inputs:
        raise ValueError('v47 native source input hashes differ')
    actual_functions = extract_functions(prepared_dir)
    baseline_functions = extract_functions(baseline_dir)
    expected_function_hashes = {name: sha(value.encode()) for name, value in actual_functions.items()}
    unchanged = ('cpu_online', 'cpu_predown', 'updater', 'prior_getter', 'trylock_getter')
    expected_unchanged_hashes = {name: sha(baseline_functions[name].encode()) for name in unchanged}
    if proof.get('source_function_sha256') != expected_function_hashes or proof.get('baseline_unchanged_function_sha256') != expected_unchanged_hashes:
        raise ValueError('v47 extracted function identity differs')
    expected_code = c_harness(actual_functions).encode('utf8')
    code_path = model / 'running_lock_model.c'
    compile_path = model / 'compile.log'
    if code_path.is_symlink() or not code_path.is_file() or code_path.read_bytes() != expected_code:
        raise ValueError('v47 generated native C differs from actual extracted functions')
    generated_sha = sha(expected_code)
    if proof.get('generated_sha256') != {name: generated_sha for name in RUNTIME_CASES}:
        raise ValueError('v47 generated C hash map differs')
    if compile_path.is_symlink() or not compile_path.is_file() or proof.get('compile_log_sha256') != sha(compile_path.read_bytes()):
        raise ValueError('v47 native compile log hash differs')
    if proof.get('logs_sha256') is None or set(proof['logs_sha256']) != set(CASES):
        raise ValueError('v47 native case log map differs')
    expected_mutations = _mutation_rejections((baseline_dir / TARGET).read_bytes(), (prepared_dir / TARGET).read_bytes())
    mutation_log_sha = sha(b'REJECT\nproduction reconstruction mismatch\n')
    for item in expected_mutations:
        item['log_sha256'] = mutation_log_sha
    expected_mutation_hashes = {item['case']: item['mutated_source_sha256'] for item in expected_mutations}
    if proof.get('mutation_results') != expected_mutations:
        raise ValueError('v47 production-transform mutation results differ')
    case_rows = proof.get('case_results')
    if not isinstance(case_rows, list) or len(case_rows) != len(CASES) or {row.get('case') for row in case_rows} != set(CASES):
        raise ValueError('v47 native result case rows differ')
    runtime_rows = {row['case']: row for row in case_rows if row['case'] in RUNTIME_CASES}
    all_case_rows = {row['case']: row for row in case_rows}
    for name in RUNTIME_CASES:
        row = runtime_rows[name]
        if row.get('accepted') is not True or type(row.get('compile_returncode')) is not int or row['compile_returncode'] != 0 or type(row.get('returncode')) is not int or row['returncode'] != 0 or row.get('generated_sha256') != generated_sha:
            raise ValueError('v47 native runtime status differs: ' + name)
        if name.startswith('repeat-transition-daif-'):
            match = re.fullmatch(r'repeat-transition-daif-([0-9a-f]{3})-irq([01])-pc([03])', name)
            if not match:
                raise ValueError('invalid v47 runtime case name')
            daif = int(match.group(1), 16) | (0x80 if match.group(2) == '1' else 0)
            expected_stdout = f'PASS mode=0 daif={daif:x} pc={match.group(3)} stores=4 locks=4/4 reads=0/0\n'
        elif name == 'start-create-error':
            expected_stdout = 'PASS mode=1 daif=145 pc=0 stores=0 locks=0/0 reads=0/0\n'
        else:
            expected_stdout = 'PASS mode=2 daif=0 pc=0 stores=0 locks=2/2 reads=3/1\n'
        log_path = model / (name + '.log')
        expected_log = 'COMPILE\nreturncode=0\nRUN\n' + expected_stdout
        if log_path.is_symlink() or not log_path.is_file() or log_path.read_text(encoding='utf8') != expected_log or proof['logs_sha256'][name] != sha(log_path.read_bytes()) or row.get('expected_stdout') != expected_stdout:
            raise ValueError('v47 native runtime transcript differs: ' + name)
    for name in set(CASES) - set(RUNTIME_CASES):
        log_path = model / (name + '.log')
        expected_log = 'REJECT\nproduction reconstruction mismatch\n'
        if log_path.is_symlink() or not log_path.is_file() or log_path.read_text(encoding='utf8') != expected_log or proof['logs_sha256'][name] != sha(log_path.read_bytes()):
            raise ValueError('v47 native mutation transcript differs: ' + name)
        if name in expected_mutation_hashes and all_case_rows[name].get('mutated_source_sha256') != expected_mutation_hashes[name]:
            raise ValueError('v47 native mutation source hash differs: ' + name)
    return True


def validate(root, build, require_package_flow=True):
    from ehld_irqsave_binding import validate as validate_irqsave
    prior_scope = (validate_irqsave(root, build) if require_package_flow else
                   validate_irqsave(root, build, require_package_flow=False))
    if type(prior_scope) is not bool:
        raise ValueError('v46 EHLD irqsave baseline scope malformed')
    enabled = assert_scope(root, build)
    if enabled and prior_scope is not True:
        raise ValueError('v47 opt-in requires a validated v46 irqsave scope')
    if not enabled:
        return False
    binding_dir = Path(root) / NATIVE_BINDING_MODEL
    if binding_dir.is_symlink() or not binding_dir.is_dir():
        raise ValueError('v47 binding mutation proof missing')
    raw = (binding_dir / 'result.json').read_bytes()
    if sha(raw) != build.get('ehld_running_lock_binding_sha256'):
        raise ValueError('v47 binding mutation proof digest differs')
    binding_proof = json.loads(raw)
    from test_ehld_running_lock_binding import CASES, PACKAGE_SCOPE_CASES
    if binding_proof.get('passed') is not True or binding_proof.get('hardware_verified') is not False:
        raise ValueError('v47 binding proof truth fields invalid')
    if binding_proof.get('cases') != list(CASES) or binding_proof.get('harness_sha256') != sha((HERE / 'test_ehld_running_lock_binding.py').read_bytes()):
        raise ValueError('v47 binding proof source/cases stale')
    if binding_proof.get('package_scope_cases') != list(PACKAGE_SCOPE_CASES):
        raise ValueError('v47 binding scope case inventory differs')
    if binding_proof.get('source_map_sha256') != sha((HERE / 'ehld_running_lock_binding.py').read_bytes()):
        raise ValueError('v47 binding source hash stale')
    if not _hash_map(binding_proof.get('generated_sha256'), CASES) or not _hash_map(binding_proof.get('logs_sha256'), CASES):
        raise ValueError('v47 binding proof files are not hash-bound')
    for name in CASES:
        code = binding_dir / (name + '.py')
        log = binding_dir / (name + '.log')
        if not code.is_file() or not log.is_file() or sha(code.read_bytes()) != binding_proof['generated_sha256'][name] or sha(log.read_bytes()) != binding_proof['logs_sha256'][name]:
            raise ValueError('v47 binding mutation evidence mismatch: ' + name)
    if require_package_flow:
        package_dir = Path(root) / PACKAGE_FLOW_MODEL
        if package_dir.is_symlink() or not package_dir.is_dir():
            raise ValueError('v47 package-flow proof missing')
        package_raw = (package_dir / 'result.json').read_bytes()
        if sha(package_raw) != build.get('ehld_running_lock_package_flow_sha256'):
            raise ValueError('v47 package-flow proof digest differs')
        package = json.loads(package_raw)
        if package.get('passed') is not True or package.get('hardware_verified') is not False:
            raise ValueError('v47 package-flow proof truth fields invalid')
        if package.get('harness_sha256') != sha((HERE / 'test_ehld_running_lock_package_flow.py').read_bytes()):
            raise ValueError('v47 package-flow harness stale')
        if package.get('package_sources_sha256') != {name: sha((HERE / name).read_bytes()) for name in PACKAGE_SOURCES}:
            raise ValueError('v47 package-flow current common dependency map differs')
        if package.get('cases') != ['production-flow-on', 'production-flow-off', 'invalid-scope-rejected']:
            raise ValueError('v47 package-flow case inventory differs')
        if package.get('case_results') != [
            {'case': 'production-flow-on', 'accepted': True, 'scope': True, 'diagnostic': True, 'rollback': False},
            {'case': 'production-flow-off', 'accepted': True, 'scope': False, 'diagnostic': False, 'rollback': False},
            {'case': 'invalid-scope-rejected', 'accepted': False},
        ]:
            raise ValueError('v47 production prepare/package case outcomes differ')
        if package.get('precheck_cases') != [
            {'case': 'on', 'accepted': True, 'scope': True, 'ready': True, 'partition_writes': False},
            {'case': 'off', 'accepted': True, 'scope': False, 'ready': True, 'partition_writes': False},
            {'case': 'invalid-pair', 'accepted': False},
        ]:
            raise ValueError('v47 precheck E2E results differ')
        if package.get('collector_cases') != [
            {'case': 'on', 'accepted': True, 'evaluation_items': 39, 'same_as_off': True, 'scope': True},
            {'case': 'off', 'accepted': True, 'evaluation_items': 39, 'same_as_on': True, 'scope': False},
            {'case': 'invalid-pair', 'accepted': False},
        ]:
            raise ValueError('v47 collector E2E results differ')
        items = package.get('collector_evaluation_items')
        items_off = package.get('collector_evaluation_items_off')
        if not isinstance(items, dict) or len(items) != 39 or items_off != items:
            raise ValueError('v47 collector 39-row ON/OFF payload differs')
        item_digest = sha(json.dumps(items, sort_keys=True, separators=(',', ':')).encode())
        if package.get('collector_evaluation_items_sha256') != item_digest:
            raise ValueError('v47 collector evaluation payload digest differs')
    return True
