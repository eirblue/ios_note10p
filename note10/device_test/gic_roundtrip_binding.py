"""Bind optional GIC CPU-interface tests to actual config/Image/source/model."""
import hashlib
import json
from pathlib import Path
from prepare_gic_roundtrip import HERE,PIN,SOURCES

def assert_scope(root,build):
    root=Path(root);p=root/'handoff.config';config=p.read_bytes() if p.exists() else b''
    enabled=b'CONFIG_NOTE10_GIC_ROUNDTRIP=y' in config.splitlines()
    image=(root/'Image').read_bytes()
    markers=(b'N10GIC1' in image,b'N10GIC2' in image)
    if enabled!=any(markers) or (enabled and not all(markers)) or enabled!=(build.get('gic_roundtrip_diagnostic') is True):
        raise ValueError('Actual GIC diagnostic scope and metadata differ')
    if enabled and (build.get('gic_roundtrip_evidence_version')!=1 or not build.get('pm_quiesce_diagnostic') or build.get('auto_return_diagnostic') is not True):
        raise ValueError('GIC roundtrip requires versioned restored PM diagnostics')
    return enabled

def validate_model(root,build):
    if not assert_scope(root,build):return False
    actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    if build.get('gic_roundtrip_sources_sha256')!=actual or build.get('gic_roundtrip_source_pin')!=PIN:
        raise ValueError('GIC diagnostic source binding differs')
    model=json.loads((Path(root)/'gic-roundtrip-model/result.json').read_text())
    rows=model.get('outcomes',[])
    if (model.get('passed') is not True or model.get('cases')!=19 or
        len(rows)!=19 or {r.get('mode') for r in rows}!=set(range(19)) or
        any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,15,17)) for r in rows) or
        model.get('source_sha256')!=actual or model.get('actual_backend_executed') is not True or
        model.get('actual_probe_executed') is not True or model.get('strict_decoder_verified') is not True or
        model.get('harness_sha256')!=hashlib.sha256((HERE/'test_gic_roundtrip_native.py').read_bytes()).hexdigest() or
        model.get('hardware_verified') is not False):raise ValueError('GIC actual-C model binding differs')
    return True
