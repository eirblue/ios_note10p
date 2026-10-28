import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from decode_reservation import checksum
from decode_pmu_settle import decode,FIELDS,TARGETS
from pmu_settle_binding import assert_scope,validate_model
from prepare_pmu_settle import HERE,SOURCES,prepare
from prepare_abox_pmu import PINS,FINAL_CORE_SHA
IDENTITY='0123456789abcdef0123456789abcdef'

def evidence(change=None,copies=2):
    text=''
    for i,target in enumerate(TARGETS):
        for copy in range(copies):
            mask=(0xffff,0x4000,0)[i]
            row=dict(seq=i*4+copy,generation=1,completed=2,index=i,target_ms=target,elapsed_ms=target+10,error=0,before=mask,state=mask,after=mask,status=0)
            if change:change(i,copy,row)
            body=f'id={IDENTITY} '+' '.join(f'{k}={row[k]:d}' if k in ('seq','generation','error','status') else f'{k}={row[k]:x}' for k in FIELDS[1:])
            text+=f'N10PST1 {body} checksum={checksum(body.encode()):08x}\n'
    return text

class DecoderTests(unittest.TestCase):
    def test_timed_states_are_observations_not_an_off_requirement(self):
        out=decode(evidence(),IDENTITY,2)
        self.assertTrue(out['pmu_settled_post_resume_observed']);self.assertEqual([out['samples'][i]['state'] for i in range(3)],[0xffff,0x4000,0])
        self.assertFalse(out['global_dma_shutdown_verified']);self.assertFalse(out['xnu_executed'])
        self.assertTrue(decode(evidence(lambda i,c,r:r.update(before=0xffff,state=0xffff,after=0xffff)),IDENTITY,2)['power_state_not_an_acceptance_condition'])
    def test_missing_corrupt_foreign_duplicate_and_conflicting_frames(self):
        good=evidence()
        for bad in (good+good,evidence(copies=1),good.replace(IDENTITY,'f'*32),good.replace('before=ffff','before=fffe'),evidence(lambda i,c,r:r.update(state=2) if i==1 and c else None),good.split('N10PST1')[0]):
            with self.assertRaises(ValueError):decode(bad,IDENTITY,2)
    def test_generation_bounds_timing_status_and_all_masks(self):
        for key,value in [('generation',0),('generation',0x100000000),('completed',3),('index',3),('seq',12),('target_ms',999),('elapsed_ms',999),('elapsed_ms',30001),('error',4),('status',1),('before',0x10000),('state',0x10000),('after',0x10000)]:
            with self.subTest(key=key),self.assertRaises(ValueError):decode(evidence(lambda i,c,r:r.update({key:value}) if i==0 else None),IDENTITY,2)
        with self.assertRaises(ValueError):decode(evidence(lambda i,c,r:r.update(elapsed_ms=20000) if i==1 else None),IDENTITY,2)
    def test_wrap_and_sequential_change_are_preserved(self):
        out=decode(evidence(lambda i,c,r:r.update(generation=0xffffffff,completed=1,before=1,state=0,after=2)),IDENTITY,1)
        self.assertEqual(out['samples'][0]['configuration_changed_mask'],3)
        self.assertTrue(out['sequential_not_atomic'])

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.config=b'CONFIG_NOTE10_PMU_SETTLE=y\nCONFIG_NOTE10_PM_NOIRQ_TEST=y\n'
        (self.root/'handoff.config').write_bytes(self.config);(self.root/'Image').write_bytes(b'N10PST1')
        actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        self.build=dict(pmu_settle_diagnostic=True,pmu_settle_evidence_version=1,pm_noirq_diagnostic=True,pm_noirq_evidence_version=1,pmu_settle_sources_sha256=actual)
        def reads(i):return i if 1<=i<=144 else 144 if i in (0,176,177,178,181) else 288 if i==180 else 1 if i==179 else 0
        self.model=dict(passed=True,cases=183,outcomes=[dict(mode=i,passed=True,accepted=i in (0,176,177,180,181),reads=reads(i)) for i in range(183)],
            worker_cases=12,worker_outcomes=[dict(mode=i,passed=True,accepted=i in (0,1,2,8,9,10,11)) for i in range(12)],
            actual_pmu_api_and_gate_executed=True,actual_delayed_worker_executed=True,all_144_read_faults_refused=True,
            no_pm_owner_or_device_locks_in_read_lane=True,default_power_requests_unchanged=True,generation_wrap_and_reset_executed=True,missing_config_refused_without_reads=True,
            hardware_verified=False,source_sha256=actual,
            regular_backend_sha256=hashlib.sha256((HERE/'abox_pmu_backend.c').read_bytes()).hexdigest(),
            noirq_backend_sha256=hashlib.sha256((HERE/'pm_noirq_backend.c').read_bytes()).hexdigest(),
            core_sha256=FINAL_CORE_SHA,pmu_api_sha256=PINS['drivers/soc/samsung/exynos-pmu.c'],cal_sha256=PINS['drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h'],
            harness_sha256=hashlib.sha256((HERE/'test_pmu_settle_native.py').read_bytes()).hexdigest())
        (self.root/'pmu-settle-model').mkdir()
    def validate(self):
        (self.root/'pmu-settle-model/result.json').write_text(json.dumps(self.model));return validate_model(self.root,self.build)
    def test_complete(self):self.assertTrue(self.validate())
    def test_scope_cannot_opt_out(self):
        for line in self.config.splitlines():
            (self.root/'handoff.config').write_bytes(self.config.replace(line+b'\n',b''))
            with self.assertRaises(ValueError):assert_scope(self.root,self.build)
        (self.root/'handoff.config').write_bytes(self.config);(self.root/'Image').write_bytes(b'')
        with self.assertRaises(ValueError):assert_scope(self.root,self.build)
    def test_model_metadata_and_sources_are_required(self):
        for container in (self.build,self.model):
            for key in list(container):
                old=container[key];container[key]=None
                with self.subTest(key=key),self.assertRaises(ValueError):self.validate()
                container[key]=old

class CompositionTests(unittest.TestCase):
    def test_guarded_prerequisites_default_off_and_single_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def put(name,raw):
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            put('kernel/power/note10_pm_noirq.c',(HERE/'pm_noirq_backend.c').read_bytes())
            put('sound/soc/samsung/abox/note10_abox_pmu.c',(HERE/'abox_pmu_backend.c').read_bytes())
            put('include/linux/note10_pm_noirq.h',(HERE/'pm_noirq_contract.h').read_bytes())
            put('kernel/power/Kconfig',b'# fixture\n')
            worker=(HERE/'pm_timer_roundtrip.c').read_bytes().replace(b'    status = 0;\nreport:',b'    n10_report_pm_noirq(pm.qgeneration);\n    status = 0;\nreport:')
            put('arch/arm64/mm/note10_pm_timer_roundtrip.c',worker)
            report=prepare(root);self.assertTrue(report['pmu_settle_diagnostic'])
            self.assertIn(b'default n',(root/'kernel/power/Kconfig').read_bytes())
            self.assertEqual((root/'arch/arm64/mm/note10_pm_timer_roundtrip.c').read_bytes().count(b'n10_arm_pmu_settle(pm.qgeneration);'),1)
            self.assertEqual((root/'sound/soc/samsung/abox/note10_pmu_settle.c').read_bytes(),(HERE/'pmu_settle_backend.c').read_bytes())
            with self.assertRaises(ValueError):prepare(root)

if __name__=='__main__':unittest.main()
