import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from decode_reservation import checksum
from decode_abox_pm import decode,FIELDS,EXTRA_FIELDS,QOS_FIELDS,LIFECYCLE_FIELDS,SYSTEM_FIELDS,TRACE_FIELDS,ORDER_FIELDS
from abox_pm_binding import assert_scope,validate_model
from prepare_abox_pm import HERE,PINS,SOURCES,PATCHED_SHA,QOS_PATCHED_SHA,QOS_TARGET_SHA,SYSTEM_PATCHED_SHA,CORE_PATCHED_SHA,event_digest,instrument
from prepare_ufs_pm import instrument_dma
ID='0123456789abcdef0123456789abcdef'

def evidence(change=None):
    result='';decimal={'seq','phase','generation','error','status'}
    for copy_index in range(2):
        for phase in range(3):
            row=dict(seq=copy_index*3+phase,phase=phase,generation=1,seen=1,error=0)
            row.update({k:0 for k in FIELDS+EXTRA_FIELDS+QOS_FIELDS+LIFECYCLE_FIELDS+SYSTEM_FIELDS+TRACE_FIELDS+ORDER_FIELDS});row.update(qos_seen=1,runtime=2,interfaces=1,rdma=4,wdma=4,events=3,enables=1,disables=1,status=0)
            if change:change(phase,copy_index,row)
            core={k:v for k,v in row.items() if k not in EXTRA_FIELDS+QOS_FIELDS+LIFECYCLE_FIELDS+SYSTEM_FIELDS+TRACE_FIELDS+ORDER_FIELDS}
            body=f'id={ID} '+' '.join(f'{k}={v:d}' if k in decimal else f'{k}={v:x}' for k,v in core.items())
            result+=f'N10ABX7 {body} checksum={checksum(body.encode()):08x}\n'
            extra={k:row[k] for k in ('seq','phase','generation')+EXTRA_FIELDS+('status',)}
            body=f'id={ID} '+' '.join(f'{k}={v:d}' if k in decimal else f'{k}={v:x}' for k,v in extra.items())
            result+=f'N10ABR1 {body} checksum={checksum(body.encode()):08x}\n'
            qos={k:row[k] for k in ('seq','phase','generation')+QOS_FIELDS+('status',)}
            body=f'id={ID} '+' '.join(f'{k}={v:d}' if k in decimal else f'{k}={v:x}' for k,v in qos.items())
            result+=f'N10ABQ1 {body} checksum={checksum(body.encode()):08x}\n'
            life={k:row[k] for k in ('seq','phase','generation')+LIFECYCLE_FIELDS+('status',)}
            body=f'id={ID} '+' '.join(f'{k}={v:d}' if k in decimal else f'{k}={v:x}' for k,v in life.items())
            result+=f'N10ABL1 {body} checksum={checksum(body.encode()):08x}\n'
            system={k:row[k] for k in ('seq','phase','generation')+SYSTEM_FIELDS+('status',)}
            body=f'id={ID} '+' '.join(f'{k}={v:d}' if k in decimal else f'{k}={v:x}' for k,v in system.items())
            result+=f'N10ABD1 {body} checksum={checksum(body.encode()):08x}\n'
            for marker,fields in (('N10ABT1',TRACE_FIELDS),('N10ABO1',ORDER_FIELDS)):
                view={k:row[k] for k in ('seq','phase','generation')+fields+('status',)}
                body=f'id={ID} '+' '.join(f'{k}={v:d}' if k in decimal else f'{k}={v:x}' for k,v in view.items())
                result+=f'{marker} {body} checksum={checksum(body.encode()):08x}\n'
    return result

class DecoderTests(unittest.TestCase):
    def test_runtime_and_async_companions_required(self):
        for marker in ('N10ABT1','N10ABO1'):
            missing='\n'.join(v for v in evidence().splitlines() if not (v.startswith(marker+' ') and 'phase=1 ' in v))
            with self.assertRaises(ValueError):decode(missing,ID,2)
    def test_runtime_queue_bounds_async_signs_and_conflicts(self):
        for values in (dict(rpm_request=5),dict(rpm_request_pending=2),dict(rpm_timer_armed=2),dict(async_fw_present=2),dict(async_resume_negative=1),dict(async_resume_after=0x80000000)):
            def change(phase,copy,row):row.update(values)
            with self.assertRaises(ValueError):decode(evidence(change),ID,2)
        for field in ('async_resume_count','enable_order'):
            def conflict(phase,copy,row):
                if phase==1 and copy==1:row[field]=1
            with self.assertRaises(ValueError):decode(evidence(conflict),ID,2)
    def test_async_inprogress_is_observation_not_reference_leak(self):
        def change(phase,copy,row):row.update(async_resume_count=1,async_resume_result=115,async_resume_negative=1,rpm_request=4,rpm_request_pending=1)
        out=decode(evidence(change),ID,2)
        self.assertFalse(out['runtime_ownership_unbalanced']);self.assertFalse(out['abox_driver_idle_state_observed'])
        self.assertTrue(out['event_orders_can_wrap'])

    def test_system_pm_companion_required_signed_and_conflict(self):
        missing='\n'.join(v for v in evidence().splitlines() if not (v.startswith('N10ABD1 ') and 'phase=1 ' in v))
        with self.assertRaises(ValueError):decode(missing,ID,2)
        for values in (dict(system_get_before_negative=1),dict(system_put_result=0x80000000),dict(system_error_put_negative=2)):
            def change(phase,copy,row):row.update(values)
            with self.assertRaises(ValueError):decode(evidence(change),ID,2)
        def conflict(phase,copy,row):
            if phase==1 and copy==1:row['system_get_after']=1
        with self.assertRaises(ValueError):decode(evidence(conflict),ID,2)
    def test_system_pm_hold_does_not_establish_leak_or_hardware_idle(self):
        def change(phase,copy,row):
            if phase>=1:row.update(system_get_count=1,system_get_before=0,system_get_after=1)
            if phase==1:row.update(usage=1,prepared=1,suspended=1)
            if phase==2:row.update(system_put_count=1,system_put_before=1,system_put_after=0)
        out=decode(evidence(change),ID,2)
        self.assertFalse(out['runtime_ownership_unbalanced'])
        self.assertFalse(out['audio_dsp_shutdown_verified'])
        self.assertTrue(out['system_pm_samples_are_not_atomic_ownership_proof'])

    def test_lifecycle_companion_required_and_old_frames_rejected(self):
        with self.assertRaises(ValueError):decode(evidence().replace('N10ABX7','N10ABX4'),ID,2)
        missing='\n'.join(v for v in evidence().splitlines() if not (v.startswith('N10ABL1 ') and 'phase=1 ' in v))
        with self.assertRaises(ValueError):decode(missing,ID,2)
    def test_late_missing_then_probe_is_observation_not_ownership_proof(self):
        def change(phase,copy,row):row.update(late_state=1,probe_get_count=1,probe_get_after=1,usage=1)
        out=decode(evidence(change),ID,2)
        self.assertTrue(out['bootstrap_lifecycle_observed']);self.assertFalse(out['abox_driver_idle_state_observed'])
        self.assertTrue(out['lifecycle_usage_samples_are_not_atomic_ownership_proof'])
    def test_invalid_lifecycle_sign_branch_and_conflict(self):
        for values in (dict(late_state=4),dict(probe_get_result=0x80000000),dict(probe_get_negative=1),dict(probe_get_before_negative=2),dict(late_state=1,late_put_count=1)):
            def change(phase,copy,row):row.update(values)
            with self.assertRaises(ValueError):decode(evidence(change),ID,2)
        def conflict(phase,copy,row):
            if phase==1 and copy==1:row['late_state']=1
        with self.assertRaises(ValueError):decode(evidence(conflict),ID,2)
    def test_qos_worker_inflight_is_not_idle_even_without_pending_bit(self):
        def change(phase,copy,row):row.update(qos_worker_starts=1,qos_worker_inflight=1)
        result=decode(evidence(change),ID,2)
        self.assertTrue(result['aud_qos_driver_observed']);self.assertFalse(result['abox_driver_idle_state_observed'])
        def invalid(phase,copy,row):row.update(qos_worker_inflight=2)
        with self.assertRaises(ValueError):decode(evidence(invalid),ID,2)
    def test_completed_qos_worker_history_is_not_current_busy_proof(self):
        def change(phase,copy,row):row.update(qos_worker_starts=1,qos_worker_finishes=1)
        self.assertTrue(decode(evidence(change),ID,2)['abox_driver_idle_state_observed'])
    def test_aud_qos_active_default_is_observed_not_shutdown(self):
        def change(phase,copy,row):row.update(qos_registered=1,qos_active=1,qos_target=100,qos_applied=100,qos_default=100,qos_first_id=0xAB0CDEFA,qos_first_value=100)
        result=decode(evidence(change),ID,2)
        self.assertTrue(result['aud_qos_driver_observed'])
        self.assertFalse(result['abox_driver_idle_state_observed'])
    def test_pending_qos_release_and_acquisition_are_not_idle(self):
        for values in (dict(qos_registered=1,qos_applied=100,qos_work_pending=1),
                       dict(qos_registered=1,qos_active=1,qos_target=120,qos_first_id=42,qos_first_value=120,qos_work_pending=1)):
            def change(phase,copy,row):row.update(values)
            result=decode(evidence(change),ID,2)
            self.assertTrue(result['abox_pm_driver_observed']);self.assertFalse(result['abox_driver_idle_state_observed'])
    def test_qos_get_put_counts_are_not_reference_balance_proof(self):
        def change(phase,copy,row):row.update(qos_gets=0xffffffff,qos_puts=1)
        result=decode(evidence(change),ID,2)
        self.assertTrue(result['qos_counts_are_not_reference_balance_proof'])
        self.assertTrue(result['abox_driver_idle_state_observed'])
    def test_qos_negative_runtime_return_is_not_idle(self):
        for values in (dict(qos_gets=1,qos_get_result=5,qos_get_negative=1),dict(qos_puts=1,qos_put_result=5,qos_put_negative=1)):
            def change(phase,copy,row):row.update(values)
            self.assertFalse(decode(evidence(change),ID,2)['abox_driver_idle_state_observed'])
    def test_qos_state_does_not_require_callback_history(self):
        def change(phase,copy,row):row.update(events=0,enables=0,disables=0,qos_registered=1,qos_applied=100)
        self.assertTrue(decode(evidence(change),ID,2)['aud_qos_driver_observed'])
        def invalid(phase,copy,row):row.update(events=0,enables=0,disables=0,qos_gets=1)
        with self.assertRaises(ValueError):decode(evidence(invalid),ID,2)
    def test_invalid_qos_bounds_and_known_owner_consistency(self):
        for values in (dict(qos_seen=0),dict(qos_error=1),dict(qos_registered=65),dict(qos_active=1),
                       dict(qos_get_negative=1),dict(qos_work_pending=2),dict(qos_default=1),
                       dict(qos_registered=1,qos_active=1,qos_target=100,qos_first_id=0xAB0CDEFA,qos_first_value=100),
                       dict(qos_registered=1,qos_active=1,qos_target=100,qos_first_id=42,qos_first_value=101)):
            def change(phase,copy,row):row.update(values)
            with self.subTest(values=values),self.assertRaises(ValueError):decode(evidence(change),ID,2)
    def test_qos_companion_is_required_and_conflicting_copies_fail(self):
        text=evidence();missing='\n'.join(v for v in text.splitlines() if not (v.startswith('N10ABQ1 ') and 'phase=1 ' in v))
        with self.assertRaises(ValueError):decode(missing,ID,2)
        def conflict(phase,copy,row):
            if phase==1 and copy==1:row['qos_registered']=1
        with self.assertRaises(ValueError):decode(evidence(conflict),ID,2)
    def test_v3_frames_cannot_satisfy_v5(self):
        with self.assertRaises(ValueError):decode(evidence().replace('N10ABX7','N10ABX3'),ID,2)
    def test_firmware_defer_is_retained_before_enable_normalization(self):
        def change(phase,copy,row):row.update(fw_downloads=1,fw_result=11,fw_negative=1)
        result=decode(evidence(change),ID,2)
        self.assertTrue(result['firmware_download_deferred'])
        self.assertFalse(result['abox_driver_idle_state_observed'])
    def test_prepare_gate_false_is_observation_not_forced_suspend(self):
        def change(phase,copy,row):row.update(notify_prepares=1,notify_stage=6,clearable_seen=1,notify_done=1)
        result=decode(evidence(change),ID,2)
        self.assertTrue(result['normal_pm_prepare_observed'])
        self.assertEqual(result['phases'][1]['snapshot']['suspend_calls'],0)
    def test_bad_prepare_return_is_valid_observation_not_idle(self):
        def change(phase,copy,row):row.update(notify_prepares=1,notify_stage=5,clearable_seen=1,clearable=1,suspend_calls=1,suspend_result=16,suspend_negative=1,notify_bad=1)
        result=decode(evidence(change),ID,2)
        self.assertTrue(result['abox_pm_driver_observed'])
        self.assertFalse(result['abox_driver_idle_state_observed'])
    def test_prepare_count_wrap_does_not_erase_observed_stage(self):
        def change(phase,copy,row):row.update(notify_stage=6,clearable_seen=1)
        self.assertTrue(decode(evidence(change),ID,2)['normal_pm_prepare_observed'])
    def test_prepare_companion_is_required_and_conflicts_are_rejected(self):
        text=evidence()
        missing='\n'.join(v for v in text.splitlines() if not (v.startswith('N10ABR1 ') and 'phase=1 ' in v))
        with self.assertRaises(ValueError):decode(missing,ID,2)
        def conflict(phase,copy,row):
            if phase==1 and copy==1:row.update(fw_downloads=1)
        with self.assertRaises(ValueError):decode(evidence(conflict),ID,2)
    def test_invalid_prepare_states_and_error_signs(self):
        for values in (dict(notify_stage=7),dict(fw_negative=1),dict(clearable=1),
                       dict(notify_stage=5,clearable_seen=1,clearable=1),
                       dict(notify_stage=6,clearable_seen=1,clearable=1,suspend_result=16,suspend_negative=1),
                       dict(notify_stage=1,clearable_seen=1)):
            def change(phase,copy,row):row.update(values)
            with self.subTest(values=values),self.assertRaises(ValueError):decode(evidence(change),ID,2)
    def test_completed_worker_history_does_not_prevent_current_idle(self):
        def change(phase,copy,row):
            row.update(cpu_gear=12,worker_starts=1,worker_finishes=1,worker_stage=4,pm_get_result=1,gate_seen=1,can_ipc=1)
        result=decode(evidence(change),ID,2)
        self.assertTrue(result['abox_driver_idle_state_observed'])
        self.assertTrue(result['cpu_gear_value_is_not_idle_proof'])
    def test_pending_work_inflight_and_negative_pm_result_are_not_idle(self):
        for values in (dict(work_pending=1),dict(worker_starts=1,worker_stage=1,worker_inflight=1),
                       dict(worker_starts=1,worker_stage=4,worker_finishes=1,gate_seen=1,pm_get_negative=1,pm_get_result=5)):
            def change(phase,copy,row):row.update(values)
            result=decode(evidence(change),ID,2)
            self.assertTrue(result['abox_pm_driver_observed'])
            self.assertFalse(result['abox_driver_idle_state_observed'])
    def test_pending_work_is_independent_of_callback_history(self):
        def change(phase,copy,row):row.update(events=0,enables=0,disables=0,work_pending=1)
        self.assertTrue(decode(evidence(change),ID,2)['abox_pm_driver_observed'])
    def test_invalid_worker_observations_are_rejected(self):
        for values in (dict(worker_starts=1,worker_stage=5),dict(can_ipc=1),dict(pm_get_negative=1),
                       dict(work_pending=2),dict(worker_inflight=1),dict(worker_starts=1,gate_seen=2)):
            def change(phase,copy,row):row.update(values)
            with self.subTest(values=values),self.assertRaises(ValueError):decode(evidence(change),ID,2)
    def test_v1_frames_are_not_v2_evidence(self):
        with self.assertRaises(ValueError):decode(evidence().replace('N10ABX7','N10ABX2'),ID,2)
    def test_worker_and_queue_counts_are_not_error_codes(self):
        def change(phase,copy,row):row.update(worker_starts=5000,worker_finishes=5000,worker_stage=4,gate_seen=1,puts=9000,gets=9000)
        self.assertTrue(decode(evidence(change),ID,2)['abox_driver_idle_state_observed'])
    def test_minimum_signed_pm_return_magnitude_is_retained(self):
        def change(phase,copy,row):row.update(worker_starts=1,worker_stage=2,worker_inflight=1,pm_get_result=0x80000000,pm_get_negative=1)
        result=decode(evidence(change),ID,2)
        self.assertEqual(result['phases'][1]['snapshot']['pm_get_result'],0x80000000)
        self.assertFalse(result['abox_driver_idle_state_observed'])
    def test_idle_is_driver_state_not_hardware_shutdown(self):
        result=decode(evidence(),ID,2)
        self.assertTrue(result['abox_driver_idle_state_observed']);self.assertFalse(result['audio_dsp_shutdown_verified'])
    def test_valid_busy_error_and_unbalanced_usage_remain_observations(self):
        for change_row in (dict(enabled=1,firmware=3,runtime=0,usage=1),dict(ipc_seen=1,ipc_called=1,ipc_error=5),dict(usage=1,usage_negative=1),dict(tail=1,queued=1),dict(depth=1)):
            def change(phase,copy,row):row.update(change_row)
            result=decode(evidence(change),ID,2)
            self.assertTrue(result['abox_pm_driver_observed']);self.assertFalse(result['abox_driver_idle_state_observed'])
    def test_invalid_or_incomplete_observations(self):
        for key,value in [('firmware',4),('runtime',4),('head',128),('queued',1),('interfaces',9),('rdma',17),('wdma',17),('enabled',2),('seen',2),('error',1),('generation',2),('status',1),('ipc_called',1),('usage_negative',1),('ipc_error',5)]:
            def change(phase,copy,row):row[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):decode(evidence(change),ID,2)
        text=evidence()
        for bad in (text+text,text.replace(ID,'f'*32),text.replace('runtime=2','runtime=0'),
            '\n'.join(line for line in text.splitlines() if 'phase=1 ' not in line)):
            with self.assertRaises(ValueError):decode(bad,ID,2)
    def test_conflicting_copy_and_generation_wrap(self):
        def conflict(phase,copy,row):
            if phase==1 and copy==1:row['audio']=1
        with self.assertRaises(ValueError):decode(evidence(conflict),ID,2)
        def wrap(phase,copy,row):row['generation']=0xffffffff
        self.assertTrue(decode(evidence(wrap),ID,1)['abox_pm_driver_observed'])
        with self.assertRaises(ValueError):decode(evidence(),ID,1)

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        self.build=dict(abox_pm_audit_diagnostic=True,abox_pm_audit_evidence_version=7,iommu_pm_audit_diagnostic=True,
            abox_core_patched_sha256=CORE_PATCHED_SHA,abox_system_patched_sha256=SYSTEM_PATCHED_SHA,abox_pm_source_pins=PINS,abox_pm_sources_sha256=actual,abox_patched_sha256=PATCHED_SHA,abox_qos_patched_sha256=QOS_PATCHED_SHA)
        self.model=dict(passed=True,cases=100,outcomes=[dict(mode=i,passed=True,accepted=i in (0,15,17,18,19,20,23,24,25,26,27,28,29,30,31,35,36,37,38,39,40,41,42,45,46,47,48,49,54,55,56,57,60,61,62,64,65,66,67,68,69,70,71,72,73,78,79,80,81,82,83,84,87,88,89,90,91,92,97,98,99)) for i in range(100)],
            core_patched_sha256=CORE_PATCHED_SHA,actual_firmware_callback_executed=True,actual_runtime_lock_sample_executed=True,system_patched_sha256=SYSTEM_PATCHED_SHA,generated_system_blocks_executed=True,source_sha256=actual,patched_driver_sha256=PATCHED_SHA,patched_qos_driver_sha256=QOS_PATCHED_SHA,qos_target_sha256=QOS_TARGET_SHA,event_blocks_sha256=event_digest(),
            generated_dma_sha256=hashlib.sha256(instrument_dma((HERE/'dma_pm_backend.c').read_bytes())).hexdigest(),
            harness_sha256=hashlib.sha256((HERE/'test_abox_pm_native.py').read_bytes()).hexdigest(),generated_lifecycle_blocks_executed=True,actual_late_initcall_executed=True,actual_backend_executed=True,
            actual_probe_executed=True,generated_event_blocks_executed=True,generated_worker_blocks_executed=True,generated_queue_blocks_executed=True,generated_prepare_blocks_executed=True,actual_qos_backend_executed=True,actual_qos_apply_executed=True,actual_qos_worker_executed=True,generated_qos_blocks_executed=True,default_off_blocks_executed=True,generated_dma_hook_executed=True,hardware_verified=False)
        (self.root/'Image').write_bytes(b'PC FIXTURE N10ABX7 N10ABR1 N10ABQ1 N10ABL1 N10ABD1 N10ABT1 N10ABO1');(self.root/'handoff.config').write_bytes(b'CONFIG_NOTE10_ABOX_PM_AUDIT=y\n');(self.root/'abox-pm-model').mkdir()
    def validate(self):
        (self.root/'abox-pm-model/result.json').write_text(json.dumps(self.model));return validate_model(self.root,self.build)
    def test_complete(self):self.assertTrue(self.validate())
    def test_scope_cannot_be_opted_out(self):
        with self.assertRaises(ValueError):assert_scope(self.root,{})
        (self.root/'handoff.config').unlink()
        with self.assertRaises(ValueError):assert_scope(self.root,{})
    def test_source_and_native_tampering(self):
        for key in self.build:
            old=self.build[key];self.build[key]=None
            with self.assertRaises(ValueError):self.validate()
            self.build[key]=old
        for key in ('core_patched_sha256','actual_firmware_callback_executed','actual_runtime_lock_sample_executed','system_patched_sha256','generated_system_blocks_executed','generated_dma_sha256','patched_qos_driver_sha256','qos_target_sha256','patched_driver_sha256','event_blocks_sha256','generated_event_blocks_executed','generated_worker_blocks_executed','generated_queue_blocks_executed','generated_prepare_blocks_executed','actual_qos_backend_executed','actual_qos_apply_executed','actual_qos_worker_executed','generated_qos_blocks_executed','default_off_blocks_executed','generated_lifecycle_blocks_executed','actual_late_initcall_executed','actual_backend_executed','actual_probe_executed','generated_dma_hook_executed','harness_sha256'):
            old=self.model[key];self.model[key]=None
            with self.assertRaises(ValueError):self.validate()
            self.model[key]=old

class PinnedRecipeTests(unittest.TestCase):
    def test_exact_original_callback_recipe(self):
        import urllib.request
        raw=urllib.request.urlopen('https://raw.githubusercontent.com/corsicanu/android_kernel_samsung_universal9820/55f042627bb7030c93550faafa117674d32b21d1/sound/soc/samsung/abox/abox.c',timeout=40).read()
        self.assertEqual(hashlib.sha256(instrument(raw)).hexdigest(),PATCHED_SHA)
        with self.assertRaises(ValueError):instrument(raw+b'changed')

if __name__=='__main__':unittest.main()
