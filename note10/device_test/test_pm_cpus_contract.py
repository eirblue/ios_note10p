import hashlib,json,tempfile,unittest,urllib.request
from pathlib import Path
from decode_reservation import checksum
from decode_pm_cpus import decode,decode_timers,SUMMARY,TIMERS
from decode_pm_noirq import DOMAIN
from prepare_pm_cpus import HERE,SOURCES,PINS,prepare
from pm_cpus_binding import assert_scope,validate_model
IDENTITY='0123456789abcdef0123456789abcdef'

def evidence(change=None,copies=2):
    text=''
    for seq in range(copies):
        for tag,fields,base in [('N10NPC1',SUMMARY,dict(generation=1,seen=1,bad=0,attempted=1,disabled=1,enabled=1,before=255,stopped=1,restored=255,cpu=0,phase=6,original=0,negative=0,error=0,error_negative=0,status=0)),
                ('N10NPD1',DOMAIN,dict(generation=1,seen=1,error=0,count=16,before=0,state=0,after=0,status=0))]:
            row=dict(base,seq=seq)
            if change:change(tag,seq,row)
            body=f'id={IDENTITY} '+' '.join(f'{k}={row[k]:d}' if k in ('seq','generation','cpu','phase','error','status') else f'{k}={row[k]:x}' for k in fields[1:])
            text+=f'{tag} {body} checksum={checksum(body.encode()):08x}\n'
    return text

def timer_evidence(change=None,copies=2):
    text=''
    for seq in range(copies):
        for cpu in range(8):
            row=dict(seq=seq,generation=2,cpu=cpu,pre_seen=1,seen=1,before=214,after=214,freq=26000000,status=0)
            if change:change(cpu,seq,row)
            body=f'id={IDENTITY} '+' '.join(f'{k}={row[k]:d}' if k in ('seq','generation','cpu','status') else f'{k}={row[k]:x}' for k in TIMERS[1:])
            text+=f'N10NCT1 {body} checksum={checksum(body.encode()):08x}\n'
    return text

class DecoderTests(unittest.TestCase):
    def test_complete_roundtrip_and_separate_domains(self):
        out=decode(evidence(),IDENTITY,2);self.assertTrue(out['pm_cpus_noirq_roundtrip_observed']);self.assertTrue(out['cpu_stop_pmu_domains_observed']);self.assertFalse(out['global_dma_shutdown_verified']);self.assertFalse(out['xnu_executed'])
    def test_missing_corrupt_foreign_duplicate_and_conflicting(self):
        good=evidence()
        for bad in (good+good,evidence(copies=1),good.replace(IDENTITY,'f'*32),good.replace('stopped=1','stopped=2'),evidence(lambda t,c,r:r.update(restored=254) if t=='N10NPC1' and c else None)):
            with self.assertRaises(ValueError):decode(bad,IDENTITY,2)
    def test_each_required_mask_operation_and_error(self):
        for key,val in [('seen',2),('bad',1),('attempted',0),('disabled',0),('enabled',0),('before',254),('stopped',3),('restored',127),('cpu',1),('phase',5),('original',5),('negative',1),('error',5),('error_negative',1),('status',1)]:
            with self.subTest(key=key),self.assertRaises(ValueError):decode(evidence(lambda t,c,r:r.update({key:val}) if t=='N10NPC1' else None),IDENTITY,2)
        for key,val in [('seen',2),('error',5),('count',15),('before',0x10000),('state',0x10000),('after',0x10000)]:
            with self.assertRaises(ValueError):decode(evidence(lambda t,c,r:r.update({key:val}) if t=='N10NPD1' else None),IDENTITY,2)
    def test_generation_wrap_and_sequential_domain_change(self):
        out=decode(evidence(lambda t,c,r:r.update(generation=0xffffffff,before=1,state=0,after=2) if t=='N10NPD1' else r.update(generation=0xffffffff)),IDENTITY,1)
        self.assertEqual(out['power_domains']['configuration_changed_mask'],3)
        with self.assertRaises(ValueError):decode(evidence(lambda t,c,r:r.update(generation=0)),IDENTITY,2)
    def test_all_eight_post_hotplug_timers(self):
        out=decode_timers(timer_evidence(),IDENTITY,2);self.assertTrue(out['pm_cpus_timer_restore_observed']);self.assertFalse(out['register_writes']);self.assertEqual(len(out['cpus']),8)
    def test_timer_fault_missing_duplicate_and_generation(self):
        good=timer_evidence()
        for bad in (good+good,timer_evidence(copies=1),good.replace('cpu=7','cpu=8'),good.replace(IDENTITY,'f'*32)):
            with self.assertRaises(ValueError):decode_timers(bad,IDENTITY,2)
        for key,val in [('generation',1),('pre_seen',0),('seen',2),('before',0),('after',0),('freq',24000000),('status',1)]:
            with self.subTest(key=key),self.assertRaises(ValueError):decode_timers(timer_evidence(lambda cpu,seq,r:r.update({key:val}) if cpu==3 else None),IDENTITY,2)

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.config=b'CONFIG_NOTE10_PM_CPUS_TEST=y\nCONFIG_NOTE10_PM_NOIRQ_TEST=y\nCONFIG_HOTPLUG_CPU=y\nCONFIG_PM_SLEEP_SMP=y\n'
        (self.root/'handoff.config').write_bytes(self.config);(self.root/'Image').write_bytes(b'N10NPC1 N10NPD1 N10NCT1')
        actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        self.build=dict(pm_cpus_diagnostic=True,pm_cpus_evidence_version=1,pm_noirq_diagnostic=True,pm_noirq_evidence_version=1,pm_cpus_sources_sha256=actual,pm_cpus_source_pins=PINS)
        from prepare_pm_noirq import FINAL_SHA
        self.model=dict(passed=True,cases=90,outcomes=[dict(mode=i,passed=True,accepted=i in (0,19,23,28,30,36,42,69,70)) for i in range(90)],
            actual_suspend_caller_and_enter_executed=True,actual_noirq_callback_hook_executed=True,actual_original_hotplug_executed=True,cpu_restore_failure_returns_eio=True,irq_syscore_machine_entry_blocked=True,partial_freeze_always_unwound=True,
            hardware_verified=False,suspend_sha256=FINAL_SHA,cpu_source_pins=PINS,source_sha256=actual,noirq_backend_sha256=hashlib.sha256((HERE/'pm_noirq_backend.c').read_bytes()).hexdigest(),harness_sha256=hashlib.sha256((HERE/'test_pm_cpus_native.py').read_bytes()).hexdigest())
        self.model['hotplug_model']=dict(passed=True,cases=28,source_sha256=PINS,actual_original_freeze_and_enable_executed=True,failed_freeze_always_requires_enable=True,void_enable_can_leave_a_cpu_offline=True,online_masks_required_for_diagnostic_acceptance=True,hardware_verified=False,outcomes=[dict(mode=i,passed=True) for i in range(28)])
        from prepare_abox_pmu import PINS as PPINS,FINAL_CORE_SHA
        def reads(i):return i if 1<=i<=48 else 0 if i in (51,52,53,54,56,57,58,59) else 48
        self.model['pmu_model']=dict(passed=True,cases=63,outcomes=[dict(mode=i,passed=True,accepted=i in (0,49,55,62),reads=reads(i)) for i in range(63)],
            actual_pmu_cpu_backend_executed=True,pinned_pmu_api_executed=True,no_device_locks_in_cpu_lane=True,all_48_read_faults_refused=True,missing_config_refused_without_reads=True,prerequisite_noirq_generation_required=True,irq_state_preserved=True,hardware_verified=False,
            core_sha256=FINAL_CORE_SHA,pmu_api_sha256=PPINS['drivers/soc/samsung/exynos-pmu.c'],cal_sha256=PPINS['drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h'],source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('abox_pmu_contract.h','abox_pmu_backend.c','pmu_domain_table.py','pm_cpus_contract.h','pm_cpus_pmu.c')},harness_sha256=hashlib.sha256((HERE/'test_pm_cpus_pmu_native.py').read_bytes()).hexdigest())
        self.model['timer_model']=dict(passed=True,cases=18,outcomes=[dict(mode=i,passed=True,accepted=i in (0,17)) for i in range(18)],actual_readback_producer_executed=True,each_cpu_mismatch_refused=True,no_register_writes=True,hardware_verified=False,producer_sha256=hashlib.sha256((HERE/'pm_cpus_timer_probe.c').read_bytes()).hexdigest(),harness_sha256=hashlib.sha256((HERE/'test_pm_cpus_timer_native.py').read_bytes()).hexdigest())
        self.model['queue_model']=dict(passed=True,cases=6,outcomes=[dict(enabled=e,mode=i,passed=True) for e in (False,True) for i in range(3)],actual_scheduler_adapter_executed=True,unbound_nonfreezable_queue_required=True,disabled_path_uses_original_queue=True,hardware_verified=False,source_sha256=hashlib.sha256((HERE/'pm_cpus_workqueue.c').read_bytes()).hexdigest(),harness_sha256=hashlib.sha256((HERE/'test_pm_cpus_queue_native.py').read_bytes()).hexdigest())
        (self.root/'pm-cpus-model').mkdir()
    def validate(self):
        (self.root/'pm-cpus-model/result.json').write_text(json.dumps(self.model));return validate_model(self.root,self.build)
    def test_complete(self):self.assertTrue(self.validate())
    def test_scope_cannot_opt_out(self):
        for line in self.config.splitlines():
            (self.root/'handoff.config').write_bytes(self.config.replace(line+b'\n',b''))
            with self.assertRaises(ValueError):assert_scope(self.root,self.build)
        (self.root/'handoff.config').write_bytes(self.config)
        for tag in (b'N10NPC1',b'N10NPD1',b'N10NCT1'):
            (self.root/'Image').write_bytes(b'N10NPC1 N10NPD1 N10NCT1'.replace(tag,b''))
            with self.assertRaises(ValueError):assert_scope(self.root,self.build)
    def test_native_models_sources_and_metadata_mandatory(self):
        for container in (self.build,self.model,self.model['hotplug_model'],self.model['pmu_model'],self.model['timer_model'],self.model['queue_model']):
            for key in list(container):
                old=container[key];container[key]=None
                with self.subTest(key=key),self.assertRaises(ValueError):self.validate()
                container[key]=old

class CompositionTests(unittest.TestCase):
    def test_pinned_cpu_prerequisites_default_off_and_report_placement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def put(n,raw):p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            for name,digest in PINS.items():
                raw=urllib.request.urlopen('https://raw.githubusercontent.com/corsicanu/android_kernel_samsung_universal9820/55f042627bb7030c93550faafa117674d32b21d1/'+name,timeout=40).read();self.assertEqual(hashlib.sha256(raw).hexdigest(),digest);put(name,raw)
            put('kernel/power/note10_pm_noirq.c',(HERE/'pm_noirq_backend.c').read_bytes());put('sound/soc/samsung/abox/note10_abox_pmu.c',(HERE/'abox_pmu_backend.c').read_bytes());put('kernel/power/Kconfig',b'# fixture\n');put('arch/arm64/mm/note10_pm_timer_roundtrip.c',(HERE/'pm_timer_roundtrip.c').read_bytes())
            report=prepare(root);self.assertTrue(report['pm_cpus_diagnostic']);self.assertIn(b'default n',(root/'kernel/power/Kconfig').read_bytes())
            worker=(root/'arch/arm64/mm/note10_pm_timer_roundtrip.c').read_bytes();self.assertLess(worker.index(b'static bool n10_timer_done;'),worker.index(b'#include "note10_pm_cpus_timer_probe.c"'));self.assertIn(b'n10_report_pm_cpu_timers(pm.qgeneration)',worker)
            self.assertEqual(worker.count(b'n10_pm_cpus_schedule('),3)
            with self.assertRaises(ValueError):prepare(root)

if __name__=='__main__':unittest.main()
