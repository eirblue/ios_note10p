"""Bind DMA PM audit to actual config/Image/source and its actual-C model."""
import hashlib
import json
from pathlib import Path
from prepare_dma_pm import HERE,PIN,SOURCES

def assert_scope(root,build):
    root=Path(root);p=root/'handoff.config'
    enabled=p.exists() and b'CONFIG_NOTE10_DMA_PM_AUDIT=y' in p.read_bytes().splitlines()
    if enabled!=(b'N10DMA1' in (root/'Image').read_bytes()) or enabled!=(build.get('dma_pm_audit_diagnostic') is True):
        raise ValueError('Actual DMA PM audit scope and metadata differ')
    if enabled and (build.get('dma_pm_audit_evidence_version')!=1 or
        build.get('gic_roundtrip_diagnostic') is not True or build.get('pm_quiesce_diagnostic') is not True or
        build.get('auto_return_diagnostic') is not True):raise ValueError('DMA PM audit prerequisites differ')
    return enabled

def validate_model(root,build):
    if not assert_scope(root,build):return False
    actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    if build.get('dma_pm_audit_sources_sha256')!=actual or build.get('dma_pm_audit_source_pin')!=PIN:
        raise ValueError('DMA PM audit source binding differs')
    model=json.loads((Path(root)/'dma-pm-model/result.json').read_text())
    rows=model.get('outcomes',[])
    if (model.get('passed') is not True or model.get('cases')!=15 or len(rows)!=15 or
        {r.get('mode') for r in rows}!=set(range(15)) or
        any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,9,10,14)) for r in rows) or
        model.get('source_sha256')!=actual or model.get('actual_backend_executed') is not True or
        model.get('actual_probe_executed') is not True or model.get('strict_decoder_verified') is not True or
        model.get('harness_sha256')!=hashlib.sha256((HERE/'test_dma_pm_native.py').read_bytes()).hexdigest() or
        model.get('hardware_verified') is not False):raise ValueError('DMA PM actual-C model binding differs')
    return True
