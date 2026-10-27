"""Bind actual ABOX observer/producer and unchanged-result callback event hooks."""
import hashlib
import json
from pathlib import Path
from prepare_abox_pm import HERE,PINS,SOURCES,PATCHED_SHA,QOS_PATCHED_SHA,QOS_TARGET_SHA,SYSTEM_PATCHED_SHA,event_digest
from prepare_ufs_pm import instrument_dma

def assert_scope(root,build):
    root=Path(root);config=root/'handoff.config'
    enabled=config.exists() and b'CONFIG_NOTE10_ABOX_PM_AUDIT=y' in config.read_bytes().splitlines()
    if enabled!=(b'N10ABX6' in (root/'Image').read_bytes()) or enabled!=(build.get('abox_pm_audit_diagnostic') is True):
        raise ValueError('Actual ABOX scope and metadata differ')
    if enabled!=(b'N10ABR1' in (root/'Image').read_bytes()):raise ValueError('ABOX prepare evidence marker differs')
    if enabled!=(b'N10ABQ1' in (root/'Image').read_bytes()):raise ValueError('QoS evidence marker differs')
    if enabled and (build.get('abox_pm_audit_evidence_version')!=6 or build.get('iommu_pm_audit_diagnostic') is not True):
        raise ValueError('ABOX observation prerequisites differ')
    if enabled!=(b'N10ABL1' in (root/'Image').read_bytes()):raise ValueError('Lifecycle evidence marker differs')
    if enabled!=(b'N10ABD1' in (root/'Image').read_bytes()):raise ValueError('System PM evidence marker differs')
    return enabled

def validate_model(root,build):
    if not assert_scope(root,build):return False
    actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    if build.get('abox_system_patched_sha256')!=SYSTEM_PATCHED_SHA or build.get('abox_pm_sources_sha256')!=actual or build.get('abox_pm_source_pins')!=PINS or build.get('abox_patched_sha256')!=PATCHED_SHA or build.get('abox_qos_patched_sha256')!=QOS_PATCHED_SHA:
        raise ValueError('ABOX source/callback binding differs')
    model=json.loads((Path(root)/'abox-pm-model/result.json').read_text());rows=model.get('outcomes',[])
    generated=hashlib.sha256(instrument_dma((HERE/'dma_pm_backend.c').read_bytes())).hexdigest()
    if (model.get('passed') is not True or model.get('cases')!=87 or len(rows)!=87 or
        {r.get('mode') for r in rows}!=set(range(87)) or
        any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,15,17,18,19,20,23,24,25,26,27,28,29,30,31,35,36,37,38,39,40,41,42,45,46,47,48,49,54,55,56,57,60,61,62,64,65,66,67,68,69,70,71,72,73,78,79,80,81,82,83,84)) for r in rows) or
        model.get('system_patched_sha256')!=SYSTEM_PATCHED_SHA or model.get('generated_system_blocks_executed') is not True or model.get('source_sha256')!=actual or model.get('patched_driver_sha256')!=PATCHED_SHA or model.get('patched_qos_driver_sha256')!=QOS_PATCHED_SHA or model.get('qos_target_sha256')!=QOS_TARGET_SHA or
        model.get('event_blocks_sha256')!=event_digest() or model.get('generated_dma_sha256')!=generated or
        any(model.get(k) is not True for k in ('generated_lifecycle_blocks_executed','actual_late_initcall_executed','actual_backend_executed','actual_probe_executed','generated_event_blocks_executed','generated_worker_blocks_executed','generated_queue_blocks_executed','generated_prepare_blocks_executed','actual_qos_backend_executed','actual_qos_apply_executed','actual_qos_worker_executed','generated_qos_blocks_executed','default_off_blocks_executed','generated_dma_hook_executed')) or
        model.get('harness_sha256')!=hashlib.sha256((HERE/'test_abox_pm_native.py').read_bytes()).hexdigest() or
        model.get('hardware_verified') is not False):raise ValueError('ABOX actual-C model binding differs')
    return True
