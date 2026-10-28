import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import urllib.request
from decode_reservation import checksum
from decode_pm_noirq import decode,SUMMARY,RESTORE,DOMAIN
from pm_noirq_binding import assert_scope,validate_model
from prepare_pm_noirq import HERE,SOURCES,PINS,BASE_SHA,FINAL_SHA,instrument
IDENTITY='0123456789abcdef0123456789abcdef'

def evidence(change=None,copies=2):
    text=''
    rows=[('N10PNQ1',SUMMARY,dict(generation=1,seen=1,bad=0,finished=1,stage=7,state=3,phase=6,late=1,late_ok=1,noirq=1,noirq_ok=1,point=1,blocked=0,ops=0,error=0,negative=0,original=0,original_negative=0,status=0)),
          ('N10PNR1',RESTORE,dict(generation=1,pre_early=5,post_early=5,pre_noirq=7,post_noirq=7,status=0)),
          ('N10PND1',DOMAIN,dict(generation=1,seen=1,error=0,count=16,before=0x4000,state=0x4000,after=0x4000,status=0))]
    decimal={'seq','generation','stage','phase','blocked','error','status'}
    for copy_index in range(copies):
        for tag,fields,base in rows:
            row=dict(base,seq=copy_index)
            if change:change(tag,copy_index,row)
            body=f'id={IDENTITY} '+' '.join(f'{k}={row[k]:d}' if k in decimal else f'{k}={row[k]:x}' for k in fields[1:])
            text+=f'{tag} {body} checksum={checksum(body.encode()):08x}\n'
    return text

class DecoderTests(unittest.TestCase):
    def test_complete_noirq_is_not_sleep_or_global_dma_proof(self):
        out=decode(evidence(),IDENTITY,2)
        self.assertTrue(out['pm_late_noirq_roundtrip_observed']);self.assertTrue(out['noirq_pmu_domain_status_observed'])
        self.assertFalse(out['real_platform_sleep_entered']);self.assertFalse(out['global_dma_shutdown_verified']);self.assertFalse(out['xnu_executed'])
        self.assertEqual(len(out['power_domains']['sampled_off']),15)
    def test_missing_corrupt_foreign_duplicate_and_conflicting_lanes(self):
        good=evidence()
        for bad in [good+good,good.replace(IDENTITY,'f'*32),evidence(copies=1),good.replace('N10PNR1','N10PNR0'),good.replace('seen=1','seen=0'),evidence(lambda t,c,r:r.update(point=0) if t=='N10PNQ1' and c else None)]:
            with self.assertRaises(ValueError):decode(bad,IDENTITY,2)
    def test_guard_owner_state_and_completion_are_mandatory(self):
        for key,value in [('seen',2),('bad',1),('finished',0),('stage',6),('state',1),('phase',5),('late',0),('late_ok',0),('noirq',0),('noirq_ok',0),('point',0),('blocked',1),('ops',1),('error',16),('negative',1),('original',16),('original_negative',1),('status',1)]:
            with self.subTest(key=key),self.assertRaises(ValueError):decode(evidence(lambda t,c,r:r.update({key:value}) if t=='N10PNQ1' else None),IDENTITY,2)
    def test_resume_error_and_domain_read_failures_cannot_be_zero_success(self):
        for tag,key,value in [('N10PNR1','post_early',6),('N10PNR1','post_noirq',8),('N10PNR1','pre_early',0x80000000),('N10PND1','error',5),('N10PND1','seen',2),('N10PND1','count',15),('N10PND1','state',0x10000),('N10PND1','before',0x10000),('N10PND1','after',0x10000)]:
            with self.subTest(tag=tag,key=key),self.assertRaises(ValueError):decode(evidence(lambda t,c,r:r.update({key:value}) if t==tag else None),IDENTITY,2)
    def test_generation_wrap_integer_bounds_and_sequential_changes(self):
        self.assertTrue(decode(evidence(lambda t,c,r:r.update(generation=0xffffffff)),IDENTITY,1)['pm_late_noirq_roundtrip_observed'])
        for key,value in [('generation',0),('generation',0x100000000),('seq',4)]:
            with self.assertRaises(ValueError):decode(evidence(lambda t,c,r:r.update({key:value})),IDENTITY,2)
        out=decode(evidence(lambda t,c,r:r.update(before=1,state=0,after=2) if t=='N10PND1' else None),IDENTITY,2)
        self.assertEqual(out['power_domains']['configuration_changed_mask'],3)
        self.assertTrue(out['sequential_domain_reads_are_not_atomic'])

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.config=b'CONFIG_NOTE10_PM_NOIRQ_TEST=y\nCONFIG_NOTE10_PM_QUIESCE=y\nCONFIG_NOTE10_ABOX_PMU_AUDIT=y\nCONFIG_PM_DEBUG=y\nCONFIG_SUSPEND=y\n'
        (self.root/'handoff.config').write_bytes(self.config);(self.root/'Image').write_bytes(b'N10PNQ1 N10PNR1 N10PND1')
        actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        self.build=dict(pm_noirq_diagnostic=True,pm_noirq_evidence_version=1,abox_pmu_audit_diagnostic=True,abox_pmu_audit_evidence_version=3,
            pm_noirq_sources_sha256=actual,pm_noirq_source_pins=PINS,pm_noirq_base_suspend_sha256=BASE_SHA,pm_noirq_final_suspend_sha256=FINAL_SHA,patched_suspend_sha256=FINAL_SHA)
        self.model=dict(passed=True,flow_cases=45,flow_outcomes=[dict(mode=i,passed=True,accepted=i in (0,19,23,28,30,36,42)) for i in range(45)],source_sha256=actual,
            final_suspend_sha256=FINAL_SHA,base_suspend_sha256=BASE_SHA,harness_sha256=hashlib.sha256((HERE/'test_pm_noirq_native.py').read_bytes()).hexdigest(),
            actual_suspend_enter_executed=True,actual_suspend_devices_caller_executed=True,legacy_disabled_path_matches_base=True,no_cpu_syscore_or_platform_entry=True,
            platform_callback_mask_refused=True,resume_error_deltas_checked=True,resume_failure_nonretryable=True,generation_wrap_executed=True,hardware_verified=False)
        from prepare_abox_pmu import PINS as PPINS,FINAL_CORE_SHA
        def reads(i):return i if 1<=i<=48 else 0 if i in (51,52,53,54,57,58,59) else 48
        self.model['pmu_noirq_model']=dict(passed=True,cases=63,outcomes=[dict(mode=i,passed=True,accepted=i in (0,49,55,56,62),reads=reads(i)) for i in range(63)],
            actual_pmu_noirq_backend_executed=True,pinned_pmu_api_executed=True,no_device_locks_in_noirq_lane=True,all_48_read_faults_refused=True,
            missing_config_refused_without_reads=True,prerequisite_regular_generation_required=True,irq_state_preserved=True,hardware_verified=False,
            core_sha256=FINAL_CORE_SHA,pmu_api_sha256=PPINS['drivers/soc/samsung/exynos-pmu.c'],cal_sha256=PPINS['drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h'],
            source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('abox_pmu_contract.h','abox_pmu_backend.c','pmu_domain_table.py')},
            harness_sha256=hashlib.sha256((HERE/'test_pm_noirq_pmu_native.py').read_bytes()).hexdigest())
        (self.root/'pm-noirq-model').mkdir()
    def validate(self):
        (self.root/'pm-noirq-model/result.json').write_text(json.dumps(self.model));return validate_model(self.root,self.build)
    def test_complete(self):self.assertTrue(self.validate())
    def test_no_config_image_or_metadata_optout(self):
        for line in self.config.splitlines():
            (self.root/'handoff.config').write_bytes(self.config.replace(line+b'\n',b''))
            with self.assertRaises(ValueError):assert_scope(self.root,self.build)
        (self.root/'handoff.config').write_bytes(self.config)
        for tag in (b'N10PNQ1',b'N10PNR1',b'N10PND1'):
            (self.root/'Image').write_bytes(b'N10PNQ1 N10PNR1 N10PND1'.replace(tag,b''))
            with self.assertRaises(ValueError):assert_scope(self.root,self.build)
    def test_model_and_source_tampering(self):
        for container in (self.build,self.model,self.model['pmu_noirq_model']):
            for key in list(container):
                old=container[key];container[key]=None
                with self.subTest(key=key),self.assertRaises(ValueError):self.validate()
                container[key]=old

class CompositionTests(unittest.TestCase):
    def test_actual_third_stage_recipe_and_original_backup(self):
        from prepare_pm_diagnostic import prepare as base_prepare,SUSPEND_SHA
        from prepare_dma_pm import prepare as dma_prepare,PIN
        from prepare_pm_noirq import prepare
        paths={**PINS,'drivers/base/power/main.c':PIN,'kernel/power/suspend.c':SUSPEND_SHA}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,digest in paths.items():
                raw=urllib.request.urlopen('https://raw.githubusercontent.com/corsicanu/android_kernel_samsung_universal9820/55f042627bb7030c93550faafa117674d32b21d1/'+name,timeout=40).read()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),digest);p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            (root/'include/linux').mkdir(parents=True,exist_ok=True);(root/'arch/arm64/mm').mkdir(parents=True)
            (root/'kernel/power/Kconfig').write_bytes(b'# PC composition fixture\n')
            (root/'arch/arm64/mm/note10_pm_timer_roundtrip.c').write_bytes((HERE/'pm_timer_roundtrip.c').read_bytes())
            base_prepare(root);dma_prepare(root);report=prepare(root)
            self.assertEqual(hashlib.sha256((root/'kernel/power/suspend-upstream.c').read_bytes()).hexdigest(),SUSPEND_SHA)
            self.assertEqual(hashlib.sha256((root/'kernel/power/suspend-base.c').read_bytes()).hexdigest(),BASE_SHA)
            self.assertEqual(hashlib.sha256((root/'kernel/power/suspend.c').read_bytes()).hexdigest(),FINAL_SHA)
            self.assertEqual(report['patched_suspend_sha256'],FINAL_SHA)
            self.assertIn(b'default n',(root/'kernel/power/Kconfig').read_bytes())
            with self.assertRaises(ValueError):instrument((root/'kernel/power/suspend.c').read_bytes())

if __name__=='__main__':unittest.main()
