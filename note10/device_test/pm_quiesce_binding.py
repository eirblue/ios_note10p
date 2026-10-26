"""Bind actual quiesce C models, prepared source and the installed kernel scope."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCES=('prepare_pm_quiesce.py','pm_quiesce_core.h','pm_devices_backend.c',
         'pm_test_contract.h','pm_decon_quiesce.c','usb_notify_quiesce.c')
DCORE='drivers/video/fbdev/exynos/dpu20/decon_core.c'


def assert_scope(root,build):
    """Derive scope from actual kernel/config, so missing metadata cannot opt out."""
    root=Path(root)
    path=root/'handoff.config'
    config=path.read_bytes() if path.exists() else b''
    enabled=b'CONFIG_NOTE10_PM_QUIESCE=y' in config.splitlines()
    marker=b'N10QSC1' in (root/'Image').read_bytes()
    declared=build.get('pm_quiesce_diagnostic') is True
    if enabled!=marker or declared!=enabled:
        raise ValueError('Actual quiesce kernel/config and declared scope differ')
    if enabled and (build.get('pm_quiesce_evidence_version')!=1 or build.get('pm_timer_diagnostic') is not True):
        raise ValueError('Quiesce kernel requires its versioned PM evidence contract')
    if config and build.get('effective_config_sha256') is not None and hashlib.sha256(config).hexdigest()!=build['effective_config_sha256']:
        raise ValueError('Quiesce scope configuration hash differs')
    return enabled


def validate_model(root,build):
    root=Path(root)
    if not assert_scope(root,build):raise ValueError('Quiesce model requested for a different kernel scope')
    from prepare_pm_quiesce import PINS
    actual={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in SOURCES}
    if (build.get('pm_quiesce_diagnostic') is not True or
            build.get('pm_quiesce_evidence_version')!=1 or
            build.get('pm_quiesce_sources_sha256')!=actual or
            build.get('pm_quiesce_source_pins')!=PINS or
            build.get('pm_quiesce_upstream_sha256')!=PINS or
            build.get('interruptible_sync_guard_preserved') is not True or
            build.get('low_level_suspend_unchanged') is not True):
        raise ValueError('Quiesce source/version/guard binding differs')
    configs=(root/'handoff.config').read_text().splitlines()
    if ('CONFIG_NOTE10_PM_QUIESCE=y' not in configs or
            b'N10QSC1' not in (root/'Image').read_bytes()):
        raise ValueError('Quiesce kernel configuration/evidence marker missing')
    model=json.loads((root/'pm-quiesce-model/result.json').read_text())
    backend_names=('pm_devices_backend.c','pm_decon_quiesce.c','pm_test_contract.h','pm_quiesce_core.h')
    wanted={name:actual[name] for name in backend_names}
    configs_seen={row.get('configuration') for row in model.get('cases',[])}
    required_configs={f'quiesce-{q}-screen-{s}' for q in (0,1) for s in (0,1)}
    identities=[(row.get('configuration'),row.get('case')) for row in model.get('cases',[])]
    required_cases={(f'quiesce-{q}-screen-{s}',case) for q in (0,1) for s in (0,1)
                    for case in (range(38) if q else (0,8,24,25))
                    if s or case not in (7,11,23)}
    required_cases|={('generated-driver-error-blocks',case) for case in range(6)}
    if (model.get('passed') is not True or model.get('case_count',0)<87 or
            model.get('case_count')!=len(model.get('cases',[])) or
            model.get('source_sha256')!=wanted or
            model.get('harness_sha256')!=hashlib.sha256((HERE/'test_pm_quiesce_native.py').read_bytes()).hexdigest() or
            not required_configs.issubset(configs_seen) or
            len(set(identities))!=len(identities) or not required_cases.issubset(identities) or
            any(row.get('passed') is not True for row in model.get('cases',[])) or
            model.get('actual_backend_executed') is not True or
            model.get('actual_decon_helper_executed') is not True or
            model.get('generated_decon_executed') is not True or
            model.get('generated_decon_sha256')!=build.get('pm_quiesce_patched_sha256',{}).get(DCORE) or
            model.get('hardware_verified') is not False):
        raise ValueError('Actual backend/DECON quiesce model binding differs')
    usb=json.loads((root/'pm-usb-model/result.json').read_text())
    usb_ids=[row.get('case') for row in usb.get('cases',[])]
    usb_required=set(range(23))|{'generated-runtime-get-0','generated-runtime-get-1'}|{'generated-after-pm-'+str(i) for i in range(16)}
    if (usb.get('passed') is not True or usb.get('case_count',0)<len(usb_required) or
            usb.get('case_count')!=len(usb.get('cases',[])) or
            len(set(usb_ids))!=len(usb_ids) or not usb_required.issubset(usb_ids) or
            usb.get('source_sha256')!={name:actual[name] for name in ('usb_notify_quiesce.c','pm_test_contract.h')} or
            usb.get('harness_sha256')!=hashlib.sha256((HERE/'test_pm_usb_native.py').read_bytes()).hexdigest() or
            usb.get('actual_usb_helper_executed') is not True or
            usb.get('generated_runtime_block_executed') is not True or
            usb.get('generated_after_pm_block_executed') is not True or
            usb.get('generated_exynos_sha256')!=build.get('pm_quiesce_patched_sha256',{}).get('drivers/usb/dwc3/dwc3-exynos.c') or
            usb.get('generated_otg_sha256')!=build.get('pm_quiesce_patched_sha256',{}).get('drivers/usb/dwc3/otg.c') or
            any(row.get('passed') is not True for row in usb.get('cases',[])) or
            usb.get('hardware_verified') is not False):
        raise ValueError('Actual USB quiesce model binding differs')
    pm=json.loads((root/'pm-timer-model/result.json').read_text())
    evidence=pm.get('quiesce_evidence_cases',[])
    if (pm.get('passed') is not True or pm.get('quiesce_evidence_verified') is not True or
            pm.get('quiesce_core_sha256')!=actual['pm_quiesce_core.h'] or
            pm.get('source_sha256')!=hashlib.sha256((HERE/'pm_timer_roundtrip.c').read_bytes()).hexdigest() or
            pm.get('backend_source_sha256')!=actual['pm_devices_backend.c'] or
            pm.get('contract_sha256')!=actual['pm_test_contract.h'] or
            len(evidence)!=8 or {row.get('mode') for row in evidence}!=set(range(100,108)) or
            any(row.get('passed') is not True or row.get('real_frame_checksums_verified') is not True or
                row.get('strict_decoder_require_quiesce') is not True for row in evidence)):
        raise ValueError('Actual PM worker quiesce evidence model binding differs')
    return {'quiesce_models_bound':True,'hardware_verified':False}
