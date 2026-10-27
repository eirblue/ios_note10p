import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from decode_reservation import checksum
from decode_abox_pmu import decode,FIELDS
from abox_pmu_binding import assert_scope,validate_model
from prepare_abox_pmu import HERE,PINS,SOURCES,CORE_PATCHED_SHA,FINAL_CORE_SHA,instrument_core,SUFFIX
from prepare_ufs_pm import instrument_dma
ID='0123456789abcdef0123456789abcdef'

def evidence(change=None):
    result=''
    for copy in range(2):
        for phase in range(3):
            for core in range(2):
                row=dict(seq=(copy*3+phase)*2+core,phase=phase,generation=1,index=core,count=2,seen=1,error=0,power=1,enable=1,standby=0x11 if core==0 else 1,status=0)
                if change:change(phase,core,copy,row)
                body=f'id={ID} '+' '.join(f'{k}={row[k]:d}' if k in ('seq','phase','generation','error','status') else f'{k}={row[k]:x}' for k in FIELDS[1:])
                result+=f'N10APM1 {body} checksum={checksum(body.encode()):08x}\n'
    for copy in range(2):
        for phase in range(3):
            generation=0xffffffff if 'generation=4294967295 ' in result else 1
            body=f'id={ID} seq={copy*3+phase} phase={phase} generation={generation} count=10 seen=1 error=0 before=0 state=0 after=0 status=0'
            result+=f'N10PDS1 {body} checksum={checksum(body.encode()):08x}\n'
    return result

class DecoderTests(unittest.TestCase):
    def test_masked_controls_are_not_power_acknowledgments(self):
        out=decode(evidence(),ID,2)
        self.assertTrue(out['abox_pmu_controls_observed']);self.assertTrue(out['control_bits_are_not_power_off_acknowledgments'])
        self.assertFalse(out['audio_dsp_shutdown_verified']);self.assertFalse(out['global_dma_shutdown_verified'])
        def zero(phase,core,copy,row):row.update(power=0,enable=0,standby=0)
        self.assertTrue(decode(evidence(zero),ID,2)['abox_pmu_controls_observed'])
    def test_missing_duplicates_corrupt_or_foreign_frames_refused(self):
        text=evidence()
        for bad in (text+text,text.replace(ID,'f'*32),text.replace('N10APM1','N10APM0'),text.replace('power=1','power=0'),
                    '\n'.join(v for v in text.splitlines() if not ('phase=1 ' in v and 'index=0 ' in v))):
            with self.assertRaises(ValueError):decode(bad,ID,2)
    def test_bounds_and_read_failure_cannot_be_zero_power_success(self):
        for key,value in (('phase',3),('index',2),('count',1),('seen',2),('error',8),('status',1),('power',2),('enable',2),('standby',2),('generation',0),('seq',24)):
            def invalid(phase,core,copy,row):row[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):decode(evidence(invalid),ID,2)
    def test_conflicting_copies_and_generation_wrap(self):
        def conflict(phase,core,copy,row):
            if phase==1 and core==1 and copy==1:row['power']=0
        with self.assertRaises(ValueError):decode(evidence(conflict),ID,2)
        def wrap(phase,core,copy,row):row['generation']=0xffffffff
        self.assertTrue(decode(evidence(wrap),ID,1)['abox_pmu_controls_observed'])
        with self.assertRaises(ValueError):decode(evidence(),ID,1)

class DomainTests(unittest.TestCase):
    def domain_evidence(self,change=None):
        from decode_abox_pmu import DOMAIN_FIELDS
        text=''
        for copy in range(2):
            for phase in range(3):
                row=dict(seq=copy*3+phase,phase=phase,generation=1,count=16,seen=1,error=0,before=0,state=0,after=0,status=0)
                if change:change(phase,copy,row)
                body=f'id={ID} '+' '.join(f'{k}={row[k]:d}' if k in ('seq','phase','generation','error','status') else f'{k}={row[k]:x}' for k in DOMAIN_FIELDS[1:])
                text+=f'N10PDS1 {body} checksum={checksum(body.encode()):08x}\n'
        return text
    def test_domain_read_errors_missing_or_invalid_cannot_be_off(self):
        from decode_abox_pmu import decode_domains
        for k,v in [('before',0x10000),('state',0x10000),('after',0x10000),('error',8),('status',1),('count',15),('seen',2),('phase',3),('seq',12),('generation',0)]:
            with self.subTest(key=k),self.assertRaises(ValueError):decode_domains(self.domain_evidence(lambda p,c,r:r.update({k:v})),ID,2)
        good=self.domain_evidence()
        for bad in [good+good,good.replace('N10PDS1','N10PDS0'),'\n'.join(x for x in good.splitlines() if 'phase=1 ' not in x),good.replace('state=0','state=1')]:
            with self.assertRaises(ValueError):decode_domains(bad,ID,2)
    def test_sequential_changes_are_exposed_and_never_prove_global_dma(self):
        from decode_abox_pmu import decode_domains
        out=decode_domains(self.domain_evidence(lambda p,c,r:r.update(before=0x1,state=0x2,after=0x4)),ID,2)
        self.assertEqual(out['phases'][1]['configuration_changed_mask'],5)
        self.assertEqual(len(out['phases'][1]['sampled_off']),13)
        self.assertTrue(out['fields_are_sequential_not_atomic']);self.assertFalse(out['global_dma_shutdown_verified'])
    def test_conflicts_or_only_one_copy_refused(self):
        from decode_abox_pmu import decode_domains
        with self.assertRaises(ValueError):decode_domains(self.domain_evidence(lambda p,c,r:r.update(state=c)),ID,2)
        with self.assertRaises(ValueError):decode_domains('\n'.join(self.domain_evidence().splitlines()[:3]),ID,2)

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.config=b'CONFIG_NOTE10_ABOX_PMU_AUDIT=y\nCONFIG_NOTE10_ABOX_FW_FAILURE_GUARD=y\nCONFIG_EXYNOS_PMU=y\nCONFIG_SOC_EXYNOS9820=y\n'
        (self.root/'handoff.config').write_bytes(self.config);(self.root/'Image').write_bytes(b'PC fixture N10APM1 N10PDS1')
        actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        self.build=dict(abox_pmu_audit_diagnostic=True,abox_pmu_audit_evidence_version=2,abox_failed_fw_resume_guard=True,
            abox_pmu_sources_sha256=actual,abox_pmu_source_pins=PINS,abox_pmu_final_core_sha256=FINAL_CORE_SHA,abox_pmu_base_core_sha256=CORE_PATCHED_SHA)
        self.model=dict(passed=True,cases=88,outcomes=[dict(mode=i,passed=True,accepted=i in (0,9,24,25,26,82)) for i in range(88)],source_sha256=actual,
            final_core_sha256=FINAL_CORE_SHA,base_core_sha256=CORE_PATCHED_SHA,generated_dma_sha256=hashlib.sha256(instrument_dma((HERE/'dma_pm_backend.c').read_bytes())).hexdigest(),
            harness_sha256=hashlib.sha256((HERE/'test_abox_pmu_native.py').read_bytes()).hexdigest(),actual_backend_executed=True,actual_producer_executed=True,
            pinned_pmu_api_executed=True,actual_domain_reads_executed=True,all_tuples_validated_before_reads=True,missing_config_refused_without_reads=True,generated_unlocked_dma_hook_executed=True,hardware_verified=False)
        (self.root/'abox-pmu-model').mkdir()
    def validate(self):
        (self.root/'abox-pmu-model/result.json').write_text(json.dumps(self.model));return validate_model(self.root,self.build)
    def test_complete(self):self.assertTrue(self.validate())
    def test_no_stub_or_scope_optout(self):
        for line in self.config.splitlines():
            (self.root/'handoff.config').write_bytes(self.config.replace(line+b'\n',b''))
            with self.assertRaises(ValueError):assert_scope(self.root,self.build)
        (self.root/'handoff.config').write_bytes(self.config)
        with self.assertRaises(ValueError):assert_scope(self.root,{})
    def test_source_and_model_tampering(self):
        for key in self.build:
            old=self.build[key];self.build[key]=None
            with self.assertRaises(ValueError):self.validate()
            self.build[key]=old
        for key in self.model:
            old=self.model[key];self.model[key]=None
            with self.assertRaises(ValueError):self.validate()
            self.model[key]=old
    def test_default_off_does_not_claim_reads(self):
        (self.root/'handoff.config').write_bytes(b'');(self.root/'Image').write_bytes(b'PC default-off fixture')
        self.assertFalse(validate_model(self.root,{}))

class CompositionTests(unittest.TestCase):
    def test_exact_guard_core_prefix_and_default_off_suffix(self):
        import urllib.request
        from prepare_abox_pm import instrument_core as base
        raw=urllib.request.urlopen('https://raw.githubusercontent.com/corsicanu/android_kernel_samsung_universal9820/55f042627bb7030c93550faafa117674d32b21d1/sound/soc/samsung/abox/abox_core.c',timeout=40).read()
        guarded=base(raw);final=instrument_core(guarded)
        self.assertEqual(hashlib.sha256(guarded).hexdigest(),CORE_PATCHED_SHA)
        self.assertEqual(hashlib.sha256(final).hexdigest(),FINAL_CORE_SHA)
        self.assertTrue(final.endswith(SUFFIX));self.assertEqual(final[:-len(SUFFIX)],guarded)
        with self.assertRaises(ValueError):instrument_core(guarded+b'changed')

if __name__=='__main__':unittest.main()
