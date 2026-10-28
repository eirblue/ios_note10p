"""Bind paired hotplug/noirq and CPU-stop PMU observations to actual scope."""
import hashlib,json
from pathlib import Path
from prepare_pm_cpus import HERE,SOURCES,PINS

def assert_scope(root,build):
    root=Path(root);p=root/'handoff.config';config=p.read_bytes().splitlines() if p.exists() else []
    enabled=b'CONFIG_NOTE10_PM_CPUS_TEST=y' in config;image=(root/'Image').read_bytes()
    if enabled!=(b'N10NPC1' in image) or enabled!=(b'N10NPD1' in image) or enabled!=(b'N10NCT1' in image) or enabled!=(build.get('pm_cpus_diagnostic') is True):raise ValueError('Actual CPU noirq scope differs')
    if enabled and (build.get('pm_cpus_evidence_version')!=1 or build.get('pm_noirq_diagnostic') is not True or
        build.get('pm_noirq_evidence_version')!=1 or any(v not in config for v in
        (b'CONFIG_NOTE10_PM_NOIRQ_TEST=y',b'CONFIG_HOTPLUG_CPU=y',b'CONFIG_PM_SLEEP_SMP=y'))):raise ValueError('CPU noirq prerequisites differ')
    return enabled

def validate_model(root,build):
    if not assert_scope(root,build):return False
    actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    if build.get('pm_cpus_sources_sha256')!=actual or build.get('pm_cpus_source_pins')!=PINS:raise ValueError('CPU source binding differs')
    m=json.loads((Path(root)/'pm-cpus-model/result.json').read_text());rows=m.get('outcomes')
    if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows):raise ValueError('Invalid CPU model outcomes')
    from prepare_pm_noirq import FINAL_SHA
    if (m.get('passed') is not True or m.get('cases')!=90 or len(rows)!=90 or {r.get('mode') for r in rows}!=set(range(90)) or
        any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,19,23,28,30,36,42,69,70)) for r in rows) or
        m.get('hardware_verified') is not False or m.get('suspend_sha256')!=FINAL_SHA or m.get('cpu_source_pins')!=PINS or
        m.get('source_sha256')!=actual or m.get('noirq_backend_sha256')!=hashlib.sha256((HERE/'pm_noirq_backend.c').read_bytes()).hexdigest() or
        m.get('harness_sha256')!=hashlib.sha256((HERE/'test_pm_cpus_native.py').read_bytes()).hexdigest() or
        any(m.get(k) is not True for k in ('actual_suspend_caller_and_enter_executed','actual_noirq_callback_hook_executed','actual_original_hotplug_executed',
            'cpu_restore_failure_returns_eio','irq_syscore_machine_entry_blocked','partial_freeze_always_unwound'))):raise ValueError('CPU integration C proof differs')
    hp=m.get('hotplug_model');pmu=m.get('pmu_model')
    if not isinstance(hp,dict) or not isinstance(pmu,dict):raise ValueError('Missing CPU nested native model')
    hp_rows=hp.get('outcomes')
    if (hp.get('passed') is not True or hp.get('cases')!=28 or not isinstance(hp_rows,list) or len(hp_rows)!=28 or
        any(not isinstance(r,dict) for r in hp_rows) or {r.get('mode') for r in hp_rows}!=set(range(28)) or
        any(r.get('passed') is not True for r in hp_rows) or hp.get('source_sha256')!=PINS or hp.get('hardware_verified') is not False or
        any(hp.get(k) is not True for k in ('actual_original_freeze_and_enable_executed','failed_freeze_always_requires_enable',
            'void_enable_can_leave_a_cpu_offline','online_masks_required_for_diagnostic_acceptance'))):raise ValueError('Original CPU hotplug model differs')
    pr=pmu.get('outcomes')
    if not isinstance(pr,list) or any(not isinstance(r,dict) for r in pr):raise ValueError('Invalid CPU-stop PMU cases')
    def reads(i):return i if 1<=i<=48 else 0 if i in (51,52,53,54,56,57,58,59) else 48
    from prepare_abox_pmu import PINS as PPINS,FINAL_CORE_SHA
    if (pmu.get('passed') is not True or pmu.get('cases')!=63 or len(pr)!=63 or {r.get('mode') for r in pr}!=set(range(63)) or
        any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,49,55,62)) or r.get('reads')!=reads(r.get('mode',-1)) for r in pr) or
        pmu.get('hardware_verified') is not False or pmu.get('core_sha256')!=FINAL_CORE_SHA or
        pmu.get('pmu_api_sha256')!=PPINS['drivers/soc/samsung/exynos-pmu.c'] or pmu.get('cal_sha256')!=PPINS['drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h'] or
        pmu.get('source_sha256')!={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('abox_pmu_contract.h','abox_pmu_backend.c','pmu_domain_table.py','pm_cpus_contract.h','pm_cpus_pmu.c')} or
        pmu.get('harness_sha256')!=hashlib.sha256((HERE/'test_pm_cpus_pmu_native.py').read_bytes()).hexdigest() or
        any(pmu.get(k) is not True for k in ('actual_pmu_cpu_backend_executed','pinned_pmu_api_executed','no_device_locks_in_cpu_lane',
            'all_48_read_faults_refused','missing_config_refused_without_reads','prerequisite_noirq_generation_required','irq_state_preserved'))):raise ValueError('CPU-stop PMU native model differs')
    timer=m.get('timer_model')
    if not isinstance(timer,dict):raise ValueError('Missing CPU timer readback model')
    tr=timer.get('outcomes')
    if (timer.get('passed') is not True or timer.get('cases')!=18 or not isinstance(tr,list) or len(tr)!=18 or
        any(not isinstance(r,dict) for r in tr) or {r.get('mode') for r in tr}!=set(range(18)) or
        any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,17)) for r in tr) or
        timer.get('hardware_verified') is not False or
        timer.get('producer_sha256')!=hashlib.sha256((HERE/'pm_cpus_timer_probe.c').read_bytes()).hexdigest() or
        timer.get('harness_sha256')!=hashlib.sha256((HERE/'test_pm_cpus_timer_native.py').read_bytes()).hexdigest() or
        any(timer.get(k) is not True for k in ('actual_readback_producer_executed','each_cpu_mismatch_refused','no_register_writes'))):raise ValueError('CPU timer readback proof differs')
    queue=m.get('queue_model')
    if not isinstance(queue,dict):raise ValueError('Missing CPU worker scheduling model')
    qr=queue.get('outcomes')
    if (queue.get('passed') is not True or queue.get('cases')!=6 or not isinstance(qr,list) or len(qr)!=6 or
        any(not isinstance(r,dict) for r in qr) or {(r.get('enabled'),r.get('mode')) for r in qr}!={(enabled,mode) for enabled in (False,True) for mode in range(3)} or
        any(r.get('passed') is not True for r in qr) or queue.get('hardware_verified') is not False or
        queue.get('source_sha256')!=hashlib.sha256((HERE/'pm_cpus_workqueue.c').read_bytes()).hexdigest() or
        queue.get('harness_sha256')!=hashlib.sha256((HERE/'test_pm_cpus_queue_native.py').read_bytes()).hexdigest() or
        any(queue.get(k) is not True for k in ('actual_scheduler_adapter_executed','unbound_nonfreezable_queue_required','disabled_path_uses_original_queue'))):raise ValueError('CPU worker scheduling C proof differs')
    return True
