"""Bind actual image/config and the timed observer to its native C models."""
import hashlib
import json
from pathlib import Path
from prepare_pmu_settle import HERE,SOURCES

def assert_scope(root,build):
    root=Path(root);p=root/'handoff.config';config=p.read_bytes().splitlines() if p.exists() else []
    enabled=b'CONFIG_NOTE10_PMU_SETTLE=y' in config
    if enabled!=(b'N10PST1' in (root/'Image').read_bytes()) or enabled!=(build.get('pmu_settle_diagnostic') is True):raise ValueError('Actual timed PMU scope differs')
    if enabled and (build.get('pmu_settle_evidence_version')!=1 or build.get('pm_noirq_diagnostic') is not True or
        build.get('pm_noirq_evidence_version')!=1 or b'CONFIG_NOTE10_PM_NOIRQ_TEST=y' not in config):raise ValueError('Timed PMU prerequisites differ')
    return enabled

def validate_model(root,build):
    if not assert_scope(root,build):return False
    actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    if build.get('pmu_settle_sources_sha256')!=actual:raise ValueError('Timed PMU source differs')
    model=json.loads((Path(root)/'pmu-settle-model/result.json').read_text())
    if not isinstance(model,dict):raise ValueError('Invalid timed PMU model')
    rows=model.get('outcomes');workers=model.get('worker_outcomes')
    if not isinstance(rows,list) or not isinstance(workers,list) or any(not isinstance(r,dict) for r in rows+workers):raise ValueError('Invalid timed PMU model cases')
    def expected_reads(mode):return mode if 1<=mode<=144 else 144 if mode in (0,176,177,178,181) else 288 if mode==180 else 1 if mode==179 else 0
    from prepare_abox_pmu import PINS,FINAL_CORE_SHA
    if (model.get('passed') is not True or model.get('cases')!=183 or len(rows)!=183 or {r.get('mode') for r in rows}!=set(range(183)) or
        any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,176,177,180,181)) or r.get('reads')!=expected_reads(r.get('mode',-1)) for r in rows) or
        model.get('worker_cases')!=12 or len(workers)!=12 or {r.get('mode') for r in workers}!=set(range(12)) or
        any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,1,2,8,9,10,11)) for r in workers) or
        model.get('source_sha256')!=actual or model.get('hardware_verified') is not False or
        model.get('harness_sha256')!=hashlib.sha256((HERE/'test_pmu_settle_native.py').read_bytes()).hexdigest() or
        model.get('regular_backend_sha256')!=hashlib.sha256((HERE/'abox_pmu_backend.c').read_bytes()).hexdigest() or
        model.get('noirq_backend_sha256')!=hashlib.sha256((HERE/'pm_noirq_backend.c').read_bytes()).hexdigest() or
        model.get('core_sha256')!=FINAL_CORE_SHA or model.get('pmu_api_sha256')!=PINS['drivers/soc/samsung/exynos-pmu.c'] or
        model.get('cal_sha256')!=PINS['drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h'] or
        any(model.get(k) is not True for k in ('actual_pmu_api_and_gate_executed','actual_delayed_worker_executed',
            'all_144_read_faults_refused','no_pm_owner_or_device_locks_in_read_lane','default_power_requests_unchanged','generation_wrap_and_reset_executed','missing_config_refused_without_reads'))):
        raise ValueError('Timed PMU native proof differs')
    return True
