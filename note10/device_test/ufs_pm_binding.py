"""Bind optional UFS audit to actual scope, source and generated-hook C model."""
import hashlib
import json
from pathlib import Path
from prepare_ufs_pm import HERE,PINS,SOURCES,instrument_dma,HCI_PATCHED_SHA

def assert_scope(root,build):
    root=Path(root);config=root/'handoff.config'
    enabled=config.exists() and b'CONFIG_NOTE10_UFS_PM_AUDIT=y' in config.read_bytes().splitlines()
    if enabled!=(b'N10UFS2' in (root/'Image').read_bytes()) or enabled!=(build.get('ufs_pm_audit_diagnostic') is True):
        raise ValueError('Actual UFS audit scope and metadata differ')
    if enabled and (build.get('ufs_pm_audit_evidence_version')!=2 or build.get('dma_pm_audit_diagnostic') is not True or
        build.get('auto_return_diagnostic') is not True):raise ValueError('UFS audit prerequisites differ')
    return enabled

def validate_model(root,build):
    if not assert_scope(root,build):return False
    actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    if build.get('ufs_hci_patched_sha256')!=HCI_PATCHED_SHA:raise ValueError('Pinned UFS HCI callback binding differs')
    if build.get('ufs_pm_audit_sources_sha256')!=actual or build.get('ufs_pm_audit_source_pins')!=PINS:
        raise ValueError('UFS audit source binding differs')
    model=json.loads((Path(root)/'ufs-pm-model/result.json').read_text())
    rows=model.get('outcomes',[])
    generated=hashlib.sha256(instrument_dma((HERE/'dma_pm_backend.c').read_bytes())).hexdigest()
    if (model.get('passed') is not True or model.get('cases')!=42 or len(rows)!=42 or
        {r.get('mode') for r in rows}!=set(range(42)) or
        any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,19)) for r in rows) or
        model.get('source_sha256')!=actual or model.get('actual_hci_backend_executed') is not True or model.get('pinned_hci_hook_executed') is not True or model.get('actual_backend_executed') is not True or
        model.get('actual_probe_executed') is not True or model.get('generated_dma_hook_executed') is not True or
        model.get('generated_dma_sha256')!=generated or build.get('ufs_pm_generated_dma_sha256')!=generated or
        model.get('harness_sha256')!=hashlib.sha256((HERE/'test_ufs_pm_native.py').read_bytes()).hexdigest() or
        model.get('hardware_verified') is not False):raise ValueError('UFS actual-C model or generated hook binding differs')
    return True
