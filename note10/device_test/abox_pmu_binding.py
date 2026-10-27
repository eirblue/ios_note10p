"""Bind real PMU scope/config, composed core source and actual-C reads model."""
import hashlib
import json
from pathlib import Path
from prepare_abox_pmu import HERE,PINS,SOURCES,FINAL_CORE_SHA,CORE_PATCHED_SHA
from prepare_ufs_pm import instrument_dma

def assert_scope(root,build):
    root=Path(root);p=root/'handoff.config';config=p.read_bytes().splitlines() if p.exists() else []
    enabled=b'CONFIG_NOTE10_ABOX_PMU_AUDIT=y' in config
    if enabled!=(b'N10APM1' in (root/'Image').read_bytes()) or enabled!=(build.get('abox_pmu_audit_diagnostic') is True):raise ValueError('Actual PMU scope differs')
    if enabled and (build.get('abox_pmu_audit_evidence_version')!=1 or build.get('abox_failed_fw_resume_guard') is not True or
        b'CONFIG_NOTE10_ABOX_FW_FAILURE_GUARD=y' not in config or b'CONFIG_EXYNOS_PMU=y' not in config):raise ValueError('Real PMU/guard prerequisites differ')
    return enabled

def validate_model(root,build):
    if not assert_scope(root,build):return False
    actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    if (build.get('abox_pmu_sources_sha256')!=actual or build.get('abox_pmu_source_pins')!=PINS or
        build.get('abox_pmu_final_core_sha256')!=FINAL_CORE_SHA or build.get('abox_pmu_base_core_sha256')!=CORE_PATCHED_SHA):raise ValueError('PMU source composition binding differs')
    model=json.loads((Path(root)/'abox-pmu-model/result.json').read_text());rows=model.get('outcomes',[])
    if not isinstance(rows,list):raise ValueError('Invalid PMU model outcomes')
    if (model.get('passed') is not True or model.get('cases')!=34 or len(rows)!=34 or
        {r.get('mode') for r in rows}!=set(range(34)) or any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,9,24,25,26)) for r in rows) or
        model.get('source_sha256')!=actual or model.get('final_core_sha256')!=FINAL_CORE_SHA or model.get('base_core_sha256')!=CORE_PATCHED_SHA or
        model.get('generated_dma_sha256')!=hashlib.sha256(instrument_dma((HERE/'dma_pm_backend.c').read_bytes())).hexdigest() or
        model.get('harness_sha256')!=hashlib.sha256((HERE/'test_abox_pmu_native.py').read_bytes()).hexdigest() or
        any(model.get(k) is not True for k in ('actual_backend_executed','actual_producer_executed','pinned_pmu_api_executed','all_tuples_validated_before_reads','missing_config_refused_without_reads','generated_unlocked_dma_hook_executed')) or
        model.get('hardware_verified') is not False):raise ValueError('PMU actual-C model binding differs')
    return True
