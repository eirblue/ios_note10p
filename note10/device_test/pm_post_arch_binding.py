"""Bind post-PM CPU evidence to its config, image, sources and native model."""
import hashlib
import json
from pathlib import Path
from prepare_pm_post_arch import HERE, PINS, SOURCES


def assert_scope(root, build):
    root = Path(root)
    path = root / 'handoff.config'
    config = path.read_bytes().splitlines() if path.exists() else []
    image = (root / 'Image').read_bytes()
    enabled = b'CONFIG_NOTE10_PM_POST_ARCH=y' in config
    if any(enabled != (marker in image) for marker in (b'N10PAR1', b'N10PCL1')) or enabled != (build.get('pm_post_arch_diagnostic') is True):
        raise ValueError('Actual post-PM architecture scope differs')
    if enabled and (build.get('pm_post_arch_evidence_version') != 1 or
        build.get('pm_cpus_diagnostic') is not True or build.get('gic_roundtrip_diagnostic') is not True or
        build.get('cpu_cache_roundtrip_diagnostic') is not True or
        any(x not in config for x in (b'CONFIG_NOTE10_PM_CPUS_TEST=y', b'CONFIG_NOTE10_GIC_ROUNDTRIP=y',
            b'CONFIG_ARM64_4K_PAGES=y', b'CONFIG_ARM64_VA_BITS=39', b'CONFIG_PGTABLE_LEVELS=3',
            b'# CONFIG_UNMAP_KERNEL_AT_EL0 is not set', b'# CONFIG_ARM64_SW_TTBR0_PAN is not set'))):
        raise ValueError('Post-PM architecture prerequisites differ')
    return enabled


def validate_model(root, build):
    if not assert_scope(root, build):
        return False
    actual = {n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    if build.get('pm_post_arch_sources_sha256') != actual or build.get('pm_post_arch_source_pins') != PINS:
        raise ValueError('Post-PM architecture source binding differs')
    model = json.loads((Path(root)/'pm-post-arch-model/result.json').read_text())
    rows = model.get('outcomes')
    if (model.get('passed') is not True or model.get('hardware_verified') is not False or
        model.get('source_sha256') != actual or model.get('cases') != 37 or not isinstance(rows,list) or
        len(rows) != 37 or any(not isinstance(r,dict) for r in rows) or
        {r.get('mode') for r in rows} != set(range(37)) or
        any(r.get('passed') is not True or r.get('accepted') != (r.get('mode') in (0,1)) for r in rows) or
        any(model.get(k) is not True for k in ('actual_producer_executed','asid_only_change_accepted',
            'per_cpu_faults_refused','no_register_writes','online_set_locked'))):
        raise ValueError('Post-PM architecture native proof differs')
    worker = model.get('worker_model')
    if not isinstance(worker,dict):
        raise ValueError('Missing prepared worker proof')
    rows = worker.get('outcomes')
    if (worker.get('cases') != 9 or not isinstance(rows,list) or len(rows) != 9 or
        any(not isinstance(r,dict) for r in rows) or {r.get('mode') for r in rows} != (set(range(8)) | {9}) or
        any(r.get('passed') is not True or r.get('accepted') != (r.get('mode') == 0) for r in rows) or
        worker.get('worker_sha256') != build.get('pm_post_arch_worker_sha256') or
        any(worker.get(k) is not True for k in ('actual_prepared_worker_executed','pm_failure_blocks_observer',
            'before_and_after_sha_failures_refused','observer_failure_refused','gic_failure_blocks_observers'))):
        raise ValueError('Prepared worker native proof differs')
    return True
