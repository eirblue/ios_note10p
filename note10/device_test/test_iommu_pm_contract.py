import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from decode_reservation import checksum
from decode_iommu_pm import decode
from iommu_pm_binding import assert_scope,validate_model
from prepare_iommu_pm import HERE,PINS,SOURCES,HELPERS_SHA,inline_helpers
from prepare_ufs_pm import instrument_dma
ID='0123456789abcdef0123456789abcdef'

def evidence(change=None,detail_change=None):
    result='';decimal={'seq','phase','generation','error','status','index','count','length'}
    def name_hash(name):
        value=2166136261
        for byte in name.encode():value=((value^byte)*16777619)&0xffffffff
        return value
    hashes=[name_hash('sysmmu.'+str(i)) for i in range(3)]
    def emit(tag,row):
        body=f'id={ID} '+' '.join(f'{k}={v}' if isinstance(v,str) else (f'{k}={v:d}' if k in decimal else f'{k}={v:x}') for k,v in row.items())
        return f'{tag} {body} checksum={checksum(body.encode()):08x}\n'
    for copy_index in range(2):
        for phase in range(3):
            row=dict(seq=copy_index*3+phase,phase=phase,generation=1,seen=1,error=0,total=3,
                active=3,suspended=0,runtime=1,manual_off=1,manual_on=1,boot_hold=1,secure_configured=1,mapped=1,syscore=1,
                prepared=3 if phase==1 else 0,pm_suspended=3 if phase==1 else 0,runtime_other=0,
                names_xor=hashes[0]^hashes[1]^hashes[2],names_sum=sum(hashes)&0xffffffff,policy_active=2,exceptions=3,status=0)
            if change:change(phase,copy_index,row)
            result+=emit('N10MMU2',row)
            for index in range(3):
                name='sysmmu.'+str(index)
                d=dict(seq=copy_index*24+phase*8+index,phase=phase,generation=row['generation'],index=index,count=3,
                    length=len(name),name=name.encode().hex(),activations=1,runtime_count=1,manual=index,active=1,suspended=0,
                    effective=int(index!=1),syscore=int(index==2),prepared=int(phase==1),pm_suspended=int(phase==1),
                    hold=int(index==1),secure=int(index==2),mapped=int(index==0),status=0)
                if detail_change:detail_change(phase,index,copy_index,d)
                result+=emit('N10MMD1',d)
    return result

class DecoderTests(unittest.TestCase):
    def test_all_active_observation_is_not_shutdown(self):
        result=decode(evidence(),ID,2)
        self.assertTrue(result['iommu_pm_driver_inventory_observed'])
        self.assertTrue(result['registered_controllers_only'])
        self.assertFalse(result['hardware_iommu_shutdown_verified'])
        self.assertFalse(result['global_dma_shutdown_verified'])
    def test_invalid_counts_status_and_stale_generation(self):
        for key,value in [('total',0),('total',65),('active',4),('suspended',4),('manual_on',4),('seen',2),('error',1),('status',1),('generation',2),('names_xor',1<<32)]:
            def change(phase,index,row):row[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):decode(evidence(change),ID,2)
    def test_inventory_change_or_conflicting_copy(self):
        for conflict in (False,True):
            def change(phase,index,row):
                if phase==1 and (index==1 or not conflict):row['names_sum']+=1
            with self.assertRaises(ValueError):decode(evidence(change),ID,2)
    def test_missing_duplicate_corrupt_and_wrong_identity(self):
        text=evidence()
        for bad in (text+text,text.replace(ID,'f'*32),text.replace('active=3','active=4'),
            ''.join(line+'\n' for line in text.splitlines() if 'phase=1 ' not in line)):
            with self.assertRaises(ValueError):decode(bad,ID,2)
    def test_generation_wrap(self):
        def change(phase,index,row):row['generation']=0xffffffff
        self.assertTrue(decode(evidence(change),ID,1)['iommu_pm_driver_inventory_observed'])
        with self.assertRaises(ValueError):decode(evidence(),ID,1)

    def test_missing_identity_cannot_fall_back_to_aggregate_pass(self):
        text=evidence()
        for bad in ('\n'.join(line for line in text.splitlines() if not line.startswith('N10MMD1')),
                    '\n'.join(line for line in text.splitlines() if not (line.startswith('N10MMD1') and 'index=1 ' in line))):
            with self.assertRaises(ValueError):decode(bad,ID,2)
    def test_identity_policy_and_count_tampering(self):
        for key,value in [('effective',1),('active',0),('runtime_count',1025),('count',2),('name','00'),('length',64),('secure',2)]:
            def tamper(phase,index,copy,row):
                if index==1:row[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):decode(evidence(detail_change=tamper),ID,2)
    def test_manual_disabled_counter_does_not_claim_hardware_activity(self):
        def change(phase,index,copy,row):
            if index==1:row['runtime_count']=1024
        result=decode(evidence(detail_change=change),ID,2)
        self.assertEqual(result['controller_details'][1]['controllers'][1]['effective'],0)
        self.assertFalse(result['hardware_iommu_shutdown_verified'])
    def test_correctly_checksummed_wrong_name_is_not_same_inventory(self):
        def tamper(phase,index,copy,row):
            if index==0:row['name']='sysmmu.x'.encode().hex()
        with self.assertRaises(ValueError):decode(evidence(detail_change=tamper),ID,2)

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        generated=hashlib.sha256(instrument_dma((HERE/'dma_pm_backend.c').read_bytes())).hexdigest()
        self.build=dict(iommu_pm_audit_diagnostic=True,iommu_pm_audit_evidence_version=2,ufs_pm_audit_diagnostic=True,
            iommu_pm_sources_sha256=actual,iommu_pm_source_pins=PINS)
        self.model=dict(passed=True,cases=25,outcomes=[dict(mode=i,passed=True,accepted=i in (0,14,18,19,21)) for i in range(25)],
            source_sha256=actual,pinned_helpers_sha256=HELPERS_SHA,generated_dma_sha256=generated,
            actual_backend_executed=True,actual_probe_executed=True,pinned_helpers_executed=True,generated_dma_hook_executed=True,
            hardware_verified=False,harness_sha256=hashlib.sha256((HERE/'test_iommu_pm_native.py').read_bytes()).hexdigest())
        (self.root/'Image').write_bytes(b'PC FIXTURE N10MMU2 N10MMD1');(self.root/'handoff.config').write_bytes(b'CONFIG_NOTE10_IOMMU_PM_AUDIT=y\n')
        (self.root/'iommu-pm-model').mkdir()
    def validate(self):
        (self.root/'iommu-pm-model/result.json').write_text(json.dumps(self.model));return validate_model(self.root,self.build)
    def test_complete(self):self.assertTrue(self.validate())
    def test_actual_scope_cannot_be_opted_out(self):
        with self.assertRaises(ValueError):assert_scope(self.root,{})
        (self.root/'handoff.config').unlink()
        with self.assertRaises(ValueError):assert_scope(self.root,{})
    def test_prerequisite_and_source_binding(self):
        for key in self.build:
            old=self.build[key];self.build[key]=None
            with self.assertRaises(ValueError):self.validate()
            self.build[key]=old
    def test_native_and_hook_tampering(self):
        for key in ('actual_backend_executed','actual_probe_executed','pinned_helpers_executed','generated_dma_hook_executed','pinned_helpers_sha256','generated_dma_sha256','harness_sha256'):
            old=self.model[key];self.model[key]=None
            with self.assertRaises(ValueError):self.validate()
            self.model[key]=old
        self.model['outcomes'][19]['accepted']=False
        with self.assertRaises(ValueError):self.validate()

class PinnedHelpersTests(unittest.TestCase):
    def test_actual_helpers(self):
        import urllib.request
        raw=urllib.request.urlopen('https://raw.githubusercontent.com/corsicanu/android_kernel_samsung_universal9820/55f042627bb7030c93550faafa117674d32b21d1/drivers/iommu/exynos-iommu.h',timeout=40).read()
        self.assertEqual(hashlib.sha256(inline_helpers(raw).encode()).hexdigest(),HELPERS_SHA)
        with self.assertRaises(ValueError):inline_helpers(raw+b'changed')

if __name__=='__main__':unittest.main()
