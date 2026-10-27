"""Bind registered-controller observations to actual build scope and native code."""
import hashlib
import json
from pathlib import Path
from prepare_iommu_pm import HERE,PINS,SOURCES,HELPERS_SHA
from prepare_ufs_pm import instrument_dma

def assert_scope(root,build):
    root=Path(root);config=root/'handoff.config'
    enabled=config.exists() and b'CONFIG_NOTE10_IOMMU_PM_AUDIT=y' in config.read_bytes().splitlines()
    if enabled!=(b'N10MMU2' in (root/'Image').read_bytes()) or enabled!=(b'N10MMD1' in (root/'Image').read_bytes()) or enabled!=(build.get('iommu_pm_audit_diagnostic') is True):
        raise ValueError('Actual IOMMU inventory scope and metadata differ')
    if enabled and b'N10MMD1' not in (root/'Image').read_bytes():raise ValueError('IOMMU identity marker missing')
    if enabled and (build.get('iommu_pm_audit_evidence_version')!=2 or build.get('ufs_pm_audit_diagnostic') is not True):
        raise ValueError('IOMMU inventory prerequisites differ')
    return enabled

def validate_model(root,build):
    if not assert_scope(root,build):return False
    actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    if build.get('iommu_pm_sources_sha256')!=actual or build.get('iommu_pm_source_pins')!=PINS:
        raise ValueError('IOMMU inventory source binding differs')
    model=json.loads((Path(root)/'iommu-pm-model/result.json').read_text());rows=model.get('outcomes',[])
    generated=hashlib.sha256(instrument_dma((HERE/'dma_pm_backend.c').read_bytes())).hexdigest()
    if (model.get('passed') is not True or model.get('cases')!=25 or len(rows)!=25 or
        {r.get('mode') for r in rows}!=set(range(25)) or
        any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,14,18,19,21)) for r in rows) or
        model.get('source_sha256')!=actual or model.get('pinned_helpers_sha256')!=HELPERS_SHA or
        any(model.get(k) is not True for k in ('actual_backend_executed','actual_probe_executed','pinned_helpers_executed','generated_dma_hook_executed')) or
        model.get('generated_dma_sha256')!=generated or
        model.get('harness_sha256')!=hashlib.sha256((HERE/'test_iommu_pm_native.py').read_bytes()).hexdigest() or
        model.get('hardware_verified') is not False):raise ValueError('IOMMU actual-C model binding differs')
    return True
