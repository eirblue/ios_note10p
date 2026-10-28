"""Bind optional guarded late/noirq scope to real Image/config and C proof."""
import hashlib
import json
from pathlib import Path
from prepare_pm_noirq import HERE,SOURCES,PINS,BASE_SHA,FINAL_SHA

def assert_scope(root,build):
    root=Path(root);p=root/'handoff.config';config=p.read_bytes().splitlines() if p.exists() else []
    enabled=b'CONFIG_NOTE10_PM_NOIRQ_TEST=y' in config
    data=(root/'Image').read_bytes()
    if enabled!=(b'N10PNQ1' in data) or enabled!=(b'N10PNR1' in data) or enabled!=(b'N10PND1' in data) or enabled!=(build.get('pm_noirq_diagnostic') is True):
        raise ValueError('Actual guarded noirq scope differs')
    if enabled and (build.get('pm_noirq_evidence_version')!=1 or build.get('abox_pmu_audit_diagnostic') is not True or
        build.get('abox_pmu_audit_evidence_version')!=3 or any(v not in config for v in
        (b'CONFIG_NOTE10_PM_QUIESCE=y',b'CONFIG_NOTE10_ABOX_PMU_AUDIT=y',b'CONFIG_PM_DEBUG=y',b'CONFIG_SUSPEND=y'))):
        raise ValueError('Noirq real prerequisites differ')
    return enabled

def validate_model(root,build):
    if not assert_scope(root,build):return False
    actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    if (build.get('pm_noirq_sources_sha256')!=actual or build.get('pm_noirq_source_pins')!=PINS or
        build.get('pm_noirq_base_suspend_sha256')!=BASE_SHA or build.get('pm_noirq_final_suspend_sha256')!=FINAL_SHA or
        build.get('patched_suspend_sha256')!=FINAL_SHA):raise ValueError('Noirq source composition differs')
    model=json.loads((Path(root)/'pm-noirq-model/result.json').read_text());rows=model.get('flow_outcomes')
    accepted=(0,19,23,28,30,36,42)
    if (not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows) or
        model.get('passed') is not True or model.get('flow_cases')!=45 or len(rows)!=45 or
        {r.get('mode') for r in rows}!=set(range(45)) or
        any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in accepted) for r in rows) or
        model.get('source_sha256')!=actual or model.get('final_suspend_sha256')!=FINAL_SHA or model.get('base_suspend_sha256')!=BASE_SHA or
        model.get('harness_sha256')!=hashlib.sha256((HERE/'test_pm_noirq_native.py').read_bytes()).hexdigest() or
        any(model.get(k) is not True for k in ('actual_suspend_enter_executed','actual_suspend_devices_caller_executed',
            'legacy_disabled_path_matches_base','no_cpu_syscore_or_platform_entry','platform_callback_mask_refused',
            'resume_error_deltas_checked','resume_failure_nonretryable','generation_wrap_executed')) or model.get('hardware_verified') is not False):
        raise ValueError('Noirq actual core caller/enter model differs')
    from prepare_abox_pmu import PINS as PPINS,FINAL_CORE_SHA
    pmu=model.get('pmu_noirq_model')
    if not isinstance(pmu,dict):raise ValueError('Missing noirq PMU model')
    outcomes=pmu.get('outcomes')
    if not isinstance(outcomes,list) or any(not isinstance(r,dict) for r in outcomes):raise ValueError('Invalid noirq PMU outcomes')
    actual_pmu={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('abox_pmu_contract.h','abox_pmu_backend.c','pmu_domain_table.py')}
    def expected_reads(mode):return mode if 1<=mode<=48 else 0 if mode in (51,52,53,54,57,58,59) else 48
    if (pmu.get('passed') is not True or pmu.get('cases')!=63 or len(outcomes)!=63 or
        {r.get('mode') for r in outcomes}!=set(range(63)) or
        any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,49,55,56,62)) or r.get('reads')!=expected_reads(r.get('mode',-1)) for r in outcomes) or
        pmu.get('source_sha256')!=actual_pmu or pmu.get('core_sha256')!=FINAL_CORE_SHA or
        pmu.get('pmu_api_sha256')!=PPINS['drivers/soc/samsung/exynos-pmu.c'] or
        pmu.get('cal_sha256')!=PPINS['drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h'] or
        pmu.get('harness_sha256')!=hashlib.sha256((HERE/'test_pm_noirq_pmu_native.py').read_bytes()).hexdigest() or
        any(pmu.get(k) is not True for k in ('actual_pmu_noirq_backend_executed','pinned_pmu_api_executed','no_device_locks_in_noirq_lane',
            'all_48_read_faults_refused','missing_config_refused_without_reads','prerequisite_regular_generation_required','irq_state_preserved')) or
        pmu.get('hardware_verified') is not False):raise ValueError('Noirq actual PMU fault model differs')
    return True
