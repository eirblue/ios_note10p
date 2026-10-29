"""Create a bounded, synthetic v46 view from a v48-only model input."""
import hashlib
import json
import shutil
from pathlib import Path

DROP_DIRS = {
    'ehld-running-lock-prepared', 'ehld-running-lock-model',
    'ehld-running-lock-binding-model', 'ehld-running-lock-package-flow-model',
}
KEEP_DIRS = (
    'abox-pm-model',
    'abox-pmu-model',
    'auto-return-model',
    'cpu-cache-model',
    'cpu-pm-failure-guard-model',
    'dma-pm-model',
    'ehld-irqsave-binding-model',
    'ehld-irqsave-model',
    'ehld-irqsave-package-flow-model',
    'ehld-irqsave-prepared',
    'ehld-lock-binding-model',
    'ehld-lock-collector-model',
    'ehld-lock-composition-model',
    'ehld-lock-decoder-model',
    'ehld-lock-final-lifecycle-model',
    'ehld-lock-native-model',
    'ehld-lock-package-flow-model',
    'ehld-lock-prepared',
    'ehld-lock-profile-inputs',
    'ehld-lock-profile-model',
    'ehld-lock-worker-model',
    'fpsimd-reference-binding-model',
    'fpsimd-reference-collector-model',
    'fpsimd-reference-decoder-model',
    'fpsimd-reference-final-lifecycle-model',
    'fpsimd-reference-native-model',
    'fpsimd-reference-package-flow-model',
    'fpsimd-reference-prepared',
    'fpsimd-reference-worker-model',
    'gic-priority-binding-model',
    'gic-priority-model',
    'gic-priority-package-flow-model',
    'gic-priority-prepared',
    'gic-roundtrip-model',
    'iommu-pm-model',
    'pm-branch-binding-model',
    'pm-branch-caller-model',
    'pm-branch-gic-source-model',
    'pm-branch-lifecycle-model',
    'pm-branch-native-model',
    'pm-branch-pmu-source-model',
    'pm-branch-prepared',
    'pm-branch-producer-model',
    'pm-branch-scope-model',
    'pm-branch-worker-model',
    'pm-build-concurrency-model',
    'pm-callbacks-binding-model',
    'pm-callbacks-coverage-model',
    'pm-callbacks-decoder-model',
    'pm-callbacks-dispatcher-model',
    'pm-callbacks-families-model',
    'pm-callbacks-integration-model',
    'pm-callbacks-lock-model',
    'pm-callbacks-prepared',
    'pm-callbacks-prepared-binding-model',
    'pm-callbacks-producer-model',
    'pm-cpus-hotplug-model',
    'pm-cpus-model',
    'pm-cpus-pmu-model',
    'pm-cpus-queue-model',
    'pm-cpus-timer-model',
    'pm-edge-binding-model',
    'pm-edge-decoder-model',
    'pm-edge-dma-model',
    'pm-edge-integration-model',
    'pm-edge-iommu-model',
    'pm-edge-syscore-model',
    'pm-irq-binding-model',
    'pm-irq-decoder-model',
    'pm-irq-integration-model',
    'pm-irq-native-model',
    'pm-noirq-model',
    'pm-noirq-pmu-model',
    'pm-post-arch-model',
    'pm-preconditions-binding-model',
    'pm-preconditions-caller-model',
    'pm-preconditions-getters-model',
    'pm-preconditions-gic-model',
    'pm-preconditions-lifecycle-model',
    'pm-preconditions-prepared',
    'pm-preconditions-producer-model',
    'pm-preconditions-scope-model',
    'pm-preconditions-worker-model',
    'pm-quiesce-model',
    'pm-timer-model',
    'pm-usb-model',
    'pmu-control-binding-model',
    'pmu-control-collector-model',
    'pmu-control-final-lifecycle-model',
    'pmu-control-native-model',
    'pmu-control-package-flow-model',
    'pmu-control-prepared',
    'pmu-control-worker-model',
    'pmu-failure-binding-model',
    'pmu-failure-model',
    'pmu-failure-package-flow-model',
    'pmu-failure-prepared',
    'pmu-settle-model',
    'pmu-state-binding-model',
    'pmu-state-collector-model',
    'pmu-state-final-lifecycle-model',
    'pmu-state-native-model',
    'pmu-state-package-flow-model',
    'pmu-state-prepared',
    'pmu-state-worker-model',
    'rcu-context-binding-model',
    'rcu-context-collector-model',
    'rcu-context-decoder-model',
    'rcu-context-final-lifecycle-model',
    'rcu-context-native-model',
    'rcu-context-package-flow-model',
    'rcu-context-prepared',
    'rcu-context-worker-model',
    'ufs-pm-model',
)
KEEP_FILES = {
    'Image', 'handoff.config', 'build-result.json', 'initramfs.cpio',
    'minimal-init.elf', 'minimal-init-model.json', 'pm-callbacks-binding-input.json',
    'pm-source-model.json', 'public-baseline.config',
}
OPTION = b'CONFIG_NOTE10_EHLD_RUNNING_LOCK_AUDIT'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _safe_model_tree(path):
    return path.is_dir() and not path.is_symlink() and all(not child.is_symlink() for child in path.rglob('*'))


def prepare(source, destination):
    source, destination = Path(source), Path(destination)
    if source.is_symlink() or not source.is_dir() or destination.exists() or destination.is_symlink():
        raise ValueError('unsafe v47 compatibility paths')
    for item in source.iterdir():
        if item.is_symlink():
            raise ValueError('symlink in v47 compatibility root')
    raw_config = (source / 'handoff.config').read_bytes()
    lines = raw_config.splitlines()
    entries = [line for line in lines if OPTION in line]
    if entries not in ([], [OPTION + b'=y'], [OPTION + b'=n'], [b'# ' + OPTION + b' is not set']):
        raise ValueError('v47 option config is duplicated or malformed')
    if entries == [OPTION + b'=y']:
        lines.remove(OPTION + b'=y')
    elif entries in ([OPTION + b'=n'], [b'# ' + OPTION + b' is not set']):
        lines.remove(entries[0])
    config = b'\n'.join(lines) + (b'\n' if raw_config.endswith(b'\n') else b'')
    report_path = source / 'build-result.json'
    if report_path.is_symlink() or not report_path.is_file():
        raise ValueError('v47 build result missing or unsafe')
    report = json.loads(report_path.read_text(encoding='utf8'))
    if report.get('build_passed') is not False:
        raise ValueError('legacy compatibility requires an explicitly synthetic outer build result')
    if report.get('ehld_running_lock_audit') is not True or type(report.get('ehld_running_lock_audit_version')) is not int or report['ehld_running_lock_audit_version'] != 2:
        raise ValueError('v48 running-lock compatibility input must be explicitly enabled at schema version 2')
    report = {key: value for key, value in report.items() if not key.startswith('ehld_running_lock_')}
    if not isinstance(report.get('ehld_lock_profile_result'), dict):
        raise ValueError('v46 EHLD profile evidence missing')
    from ehld_lock_profile import verify_config
    report['ehld_lock_profile_result'] = verify_config(config)
    base = Path(__file__).resolve().parent

    def digest(name):
        rel = Path(name)
        path = base / rel
        if rel.is_absolute() or '..' in rel.parts or path.is_symlink() or not path.is_file():
            raise ValueError('unsafe package dependency name in compatibility report')
        return sha(path.read_bytes())

    # Common package files changed with v47; refresh every historical package map.
    for key, value in list(report.items()):
        if key.endswith('_package_sources_sha256'):
            if not isinstance(value, dict) or not all(isinstance(name, str) for name in value):
                raise ValueError('invalid historical package source map')
            report[key] = {name: digest(name) for name in value}
        elif key.endswith('_collector_dependencies_sha256'):
            if not isinstance(value, dict) or not all(isinstance(name, str) for name in value):
                raise ValueError('invalid historical collector dependency map')
            report[key] = {name: digest(name) for name in value}
    from ehld_lock_binding import SOURCES as lock_sources, PACKAGE_SOURCES as lock_packages, COLLECTOR_DEPENDENCIES as lock_collectors
    from rcu_context_binding import SOURCES as rcu_sources, PACKAGE_SOURCES as rcu_packages, COLLECTOR_DEPENDENCIES as rcu_collectors
    report['ehld_lock_sources_sha256'] = {name: digest(name) for name in lock_sources}
    report['ehld_lock_package_sources_sha256'] = {name: digest(name) for name in lock_packages}
    report['ehld_lock_collector_dependencies_sha256'] = {name: digest(name) for name in lock_collectors}
    report['rcu_context_sources_sha256'] = {name: digest(name) for name in rcu_sources}
    report['rcu_context_package_sources_sha256'] = {name: digest(name) for name in rcu_packages}
    report['rcu_context_collector_dependencies_sha256'] = {name: digest(name) for name in rcu_collectors}

    # Explicit root allowlist: never copy kernel objects, source, archive or unknown files.
    destination.mkdir(parents=True)
    for item in source.iterdir():
        keep_dir = item.is_dir() and item.name in KEEP_DIRS and item.name not in DROP_DIRS
        keep_file = item.is_file() and item.name in KEEP_FILES
        if not (keep_dir or keep_file):
            continue
        target = destination / item.name
        if keep_dir:
            if not _safe_model_tree(item):
                raise ValueError('unsafe nested model directory: ' + item.name)
            shutil.copytree(item, target)
        else:
            shutil.copyfile(item, target)
    if not (destination / 'Image').is_file():
        raise ValueError('v47 model Image missing')
    if not (destination / 'ehld-irqsave-prepared').is_dir():
        raise ValueError('v46 prepared source snapshot missing in compatibility input')
    (destination / 'handoff.config').write_bytes(config)
    from rcu_context_binding import MARKERS as RCU_MARKERS
    from ehld_lock_binding import MARKERS as EHLD_MARKERS
    image = bytearray(4096)
    image[56:60] = b'ARM\x64'
    markers = b''.join(RCU_MARKERS + EHLD_MARKERS)
    image[128:128 + len(markers)] = markers
    image = bytes(image)
    (destination / 'Image').write_bytes(image)
    report.update(
        build_passed=False,
        compatibility_model_only=True,
        hardware_verified=False,
        image_sha256=sha(image),
        image_size=len(image),
        effective_config_sha256=sha(config),
    )
    (destination / 'build-result.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf8', newline='\n')
    return destination
